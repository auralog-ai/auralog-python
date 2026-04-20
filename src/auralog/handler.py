from __future__ import annotations

import logging
from typing import Any

from .logger import Logger
from .types import LogLevel

# stdlib logging level -> auralog level
_LEVEL_MAP: dict[int, LogLevel] = {
    logging.DEBUG: LogLevel.DEBUG,
    logging.INFO: LogLevel.INFO,
    logging.WARNING: LogLevel.WARN,
    logging.ERROR: LogLevel.ERROR,
    logging.CRITICAL: LogLevel.FATAL,
}

# Fields stdlib puts on LogRecord that we never want to leak into metadata.
_RESERVED: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)


class AuralogHandler(logging.Handler):
    """
    stdlib logging.Handler that forwards records to the auralog Logger.

    Usage:
        import logging
        from auralog import init, AuralogHandler
        init(api_key="...", environment="prod")
        logging.getLogger().addHandler(AuralogHandler())

    If `logger` is not provided, uses the module-level auralog Logger set up by init().
    """

    def __init__(self, logger: Logger | None = None, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self._logger = logger

    def _resolve_logger(self) -> Logger | None:
        if self._logger is not None:
            return self._logger
        from . import _state

        return _state.logger

    def emit(self, record: logging.LogRecord) -> None:
        try:
            target = self._resolve_logger()
            if target is None:
                return  # SDK not initialized; drop silently.

            level = _LEVEL_MAP.get(record.levelno, LogLevel.INFO)
            msg = record.getMessage()
            metadata = self._extract_metadata(record) or None

            exc: BaseException | None = None
            if record.exc_info and isinstance(record.exc_info, tuple):
                _, exc_val, _ = record.exc_info
                if isinstance(exc_val, BaseException):
                    exc = exc_val

            if level == LogLevel.FATAL:
                target.fatal(msg, metadata=metadata, exc_info=exc)
            elif level == LogLevel.ERROR:
                target.error(msg, metadata=metadata, exc_info=exc)
            elif level == LogLevel.WARN:
                target.warn(msg, metadata=metadata)
            elif level == LogLevel.INFO:
                target.info(msg, metadata=metadata)
            else:
                target.debug(msg, metadata=metadata)
        except Exception:
            self.handleError(record)

    def _extract_metadata(self, record: logging.LogRecord) -> dict[str, Any]:
        return {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
