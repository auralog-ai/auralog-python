from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

DEFAULT_ENDPOINT = "https://ingest.auralogs.ai"
DEFAULT_FLUSH_INTERVAL_SECONDS = 5.0
DEFAULT_ENVIRONMENT = "production"
DEFAULT_MAX_QUEUE_SIZE = 1000

# A baseline metadata map merged into every emitted log entry. Accepts either:
#   - a static `dict[str, Any]` (resolved once when set), or
#   - a zero-arg callable returning `dict[str, Any]` (invoked at every emit
#     for late binding — e.g. `lambda: {"user_id": current_user.id}`).
# Synchronous only — coroutine/awaitable returns are treated as failure.
GlobalMetadata = dict[str, Any] | Callable[[], dict[str, Any]]


@dataclass
class AuralogsConfig:
    api_key: str
    environment: str = DEFAULT_ENVIRONMENT
    endpoint: str = DEFAULT_ENDPOINT
    flush_interval: float = DEFAULT_FLUSH_INTERVAL_SECONDS
    capture_errors: bool = True
    trace_id: str | None = None
    global_metadata: GlobalMetadata | None = field(default=None)
    # Maximum number of buffered (non-error) log entries held in memory while
    # waiting for the next flush. When the buffer would exceed this size the
    # oldest entries are dropped first so an unreachable ingest endpoint can
    # never OOM the host process. Errors bypass the buffer entirely.
    max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
    # Reject endpoints that aren't `https://...` unless this is explicitly True.
    # Prevents a misconfigured `endpoint=http://...` from silently downgrading
    # every POST to plaintext.
    allow_insecure_endpoint: bool = False

    def __post_init__(self) -> None:
        # Normalize before validating so trailing-slash variations don't slip
        # past the scheme check.
        self.endpoint = self.endpoint.rstrip("/")
        # Per RFC 3986 §3.1, URI schemes are case-insensitive. Lowercase the
        # scheme prefix before comparison so `HTTPS://...` isn't wrongly
        # rejected as plaintext.
        if not self.allow_insecure_endpoint and not self.endpoint.lower().startswith("https://"):
            raise ValueError(
                "auralogs: endpoint must use https:// "
                f"(got {self.endpoint!r}). Pass allow_insecure_endpoint=True to "
                "opt in to plaintext (e.g. for a local development ingest)."
            )
        # `max_queue_size <= 0` would silently swallow every non-error log
        # (`deque(maxlen=0)` accepts appends but discards them immediately).
        # Reject up front so the failure mode is loud rather than invisible.
        if self.max_queue_size <= 0:
            raise ValueError(
                "auralogs: max_queue_size must be a positive integer "
                f"(got {self.max_queue_size!r})."
            )
