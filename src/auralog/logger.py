from __future__ import annotations

import traceback
import uuid
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

    def __init__(
        self,
        *,
        environment: str,
        sink: Callable[[LogEntry], None],
        trace_id: str | None = None,
    ) -> None:
        self._environment = environment
        self._sink = sink
        self._trace_id = trace_id if trace_id is not None else str(uuid.uuid4())

    def get_trace_id(self) -> str:
        return self._trace_id

    def set_trace_id(self, trace_id: str) -> None:
        self._trace_id = trace_id

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
        entry_trace_id = self._trace_id
        clean_meta = metadata
        if metadata is not None and "traceId" in metadata:
            entry_trace_id = str(metadata["traceId"])
            clean_meta = {k: v for k, v in metadata.items() if k != "traceId"}
            if not clean_meta:
                clean_meta = None
        self._sink(
            LogEntry(
                level=level,
                message=message,
                environment=self._environment,
                timestamp=self._now(),
                metadata=clean_meta,
                stack_trace=stack,
                trace_id=entry_trace_id,
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
