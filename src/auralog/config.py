from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

DEFAULT_ENDPOINT = "https://ingest.auralog.ai"
DEFAULT_FLUSH_INTERVAL_SECONDS = 5.0
DEFAULT_ENVIRONMENT = "production"

# A baseline metadata map merged into every emitted log entry. Accepts either:
#   - a static `dict[str, Any]` (resolved once when set), or
#   - a zero-arg callable returning `dict[str, Any]` (invoked at every emit
#     for late binding — e.g. `lambda: {"user_id": current_user.id}`).
# Synchronous only — coroutine/awaitable returns are treated as failure.
GlobalMetadata = dict[str, Any] | Callable[[], dict[str, Any]]


@dataclass
class AuralogConfig:
    api_key: str
    environment: str = DEFAULT_ENVIRONMENT
    endpoint: str = DEFAULT_ENDPOINT
    flush_interval: float = DEFAULT_FLUSH_INTERVAL_SECONDS
    capture_errors: bool = True
    trace_id: str | None = None
    global_metadata: GlobalMetadata | None = field(default=None)
