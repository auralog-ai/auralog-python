from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50

    def serialize(self) -> str:
        return self.name.lower()


def is_at_or_above(level: LogLevel, threshold: LogLevel) -> bool:
    return level >= threshold


@dataclass
class LogEntry:
    level: LogLevel
    message: str
    environment: str
    timestamp: str
    metadata: dict[str, Any] | None = None
    stack_trace: str | None = None

    def to_wire(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "level": self.level.serialize(),
            "message": self.message,
            "environment": self.environment,
            "timestamp": self.timestamp,
        }
        if self.metadata is not None:
            out["metadata"] = self.metadata
        if self.stack_trace is not None:
            out["stackTrace"] = self.stack_trace
        return out
