from __future__ import annotations

import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .types import LogEntry, LogLevel


class Logger:
    """
    Emits structured log entries to a sink callable (typically Transport.send).

    Separating the logger from the transport makes both easier to test
    and keeps a clean boundary between "what to log" and "how to send".
    """

    def __init__(self, *, environment: str, sink: Callable[[LogEntry], None]) -> None:
        self._environment = environment
        self._sink = sink

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _emit(
        self,
        level: LogLevel,
        message: str,
        metadata: dict[str, Any] | None,
        exc_info: BaseException | None,
    ) -> None:
        stack: str | None = None
        if exc_info is not None:
            stack = "".join(
                traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)
            )
        self._sink(
            LogEntry(
                level=level,
                message=message,
                environment=self._environment,
                timestamp=self._now(),
                metadata=metadata,
                stack_trace=stack,
            )
        )

    def debug(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.DEBUG, message, metadata, None)

    def info(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.INFO, message, metadata, None)

    def warn(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.WARN, message, metadata, None)

    def error(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._emit(LogLevel.ERROR, message, metadata, exc_info)

    def fatal(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._emit(LogLevel.FATAL, message, metadata, exc_info)
