"""
Auralog — agentic logging and application awareness.

Public surface:
    init(api_key, environment, endpoint=..., flush_interval=..., capture_errors=...)
    shutdown()
    auralog.debug / info / warn / error / fatal
    AuralogHandler  (stdlib logging bridge)
"""

from __future__ import annotations

import atexit
from typing import Any

from . import _state
from .config import AuralogConfig, GlobalMetadata
from .handler import AuralogHandler
from .logger import Logger
from .transport import Transport

__all__ = [
    "AuralogHandler",
    "GlobalMetadata",
    "auralog",
    "get_trace_id",
    "init",
    "set_trace_id",
    "shutdown",
]


def init(
    *,
    api_key: str,
    environment: str = "production",
    endpoint: str = "https://ingest.auralog.ai",
    flush_interval: float = 5.0,
    capture_errors: bool = True,
    trace_id: str | None = None,
    global_metadata: GlobalMetadata | None = None,
) -> None:
    """
    Initialize the SDK. Idempotent — calling `init` again replaces the prior config
    and flushes the previous transport.

    `global_metadata`: optional baseline metadata merged into every log entry
    before transport. Accepts either a static `dict[str, Any]` or a zero-arg
    callable returning `dict[str, Any]` (invoked at every emit for late binding).
    Per-call `metadata` keys win on collision. Synchronous only — coroutine
    returns are treated as failure and the entry ships without global_metadata.
    """
    shutdown()

    cfg = AuralogConfig(
        api_key=api_key,
        environment=environment,
        endpoint=endpoint,
        flush_interval=flush_interval,
        capture_errors=capture_errors,
        trace_id=trace_id,
        global_metadata=global_metadata,
    )
    transport = Transport(
        api_key=cfg.api_key,
        endpoint=cfg.endpoint,
        flush_interval=cfg.flush_interval,
    )
    logger = Logger(
        environment=cfg.environment,
        sink=transport.send,
        trace_id=cfg.trace_id,
        global_metadata=cfg.global_metadata,
    )

    _state.transport = transport
    _state.logger = logger

    if cfg.capture_errors:
        from .error_capture import install_error_capture

        install_error_capture(logger)

    if not _state.atexit_registered:
        atexit.register(shutdown)
        _state.atexit_registered = True


def shutdown() -> None:
    """Flush pending logs and stop the background thread. Safe to call multiple times."""
    try:
        from .error_capture import uninstall_error_capture

        uninstall_error_capture()
    except Exception:
        pass

    if _state.transport is not None:
        _state.transport.shutdown()
        _state.transport = None
    _state.logger = None


def _require_logger() -> Logger:
    if _state.logger is None:
        raise RuntimeError("auralog.init() must be called before using the logger")
    return _state.logger


def get_trace_id() -> str:
    """Return the current trace ID. Auto-generated at init unless overridden."""
    return _require_logger().get_trace_id()


def set_trace_id(trace_id: str) -> None:
    """Replace the current trace ID. Use to propagate an incoming trace ID from another service."""
    _require_logger().set_trace_id(trace_id)


class _AuralogProxy:
    """
    Call-site façade that delegates to the module-level Logger. Raises a clear
    RuntimeError if `init` hasn't been called — otherwise a missing init would
    be a silent no-op that's very hard to debug.
    """

    def _require(self) -> Logger:
        if _state.logger is None:
            raise RuntimeError("auralog.init() must be called before using the logger")
        return _state.logger

    def debug(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._require().debug(message, metadata)

    def info(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._require().info(message, metadata)

    def warn(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._require().warn(message, metadata)

    def error(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._require().error(message, metadata, exc_info)

    def fatal(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._require().fatal(message, metadata, exc_info)


auralog = _AuralogProxy()
