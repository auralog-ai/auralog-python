from __future__ import annotations

from auralog.logger import Logger
from auralog.types import LogEntry, LogLevel


def test_logger_methods_emit_entries_with_correct_levels():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.debug("d")
    log.info("i")
    log.warn("w")
    log.error("e")
    log.fatal("f")
    assert [e.level for e in captured] == [
        LogLevel.DEBUG,
        LogLevel.INFO,
        LogLevel.WARN,
        LogLevel.ERROR,
        LogLevel.FATAL,
    ]
    assert all(e.environment == "prod" for e in captured)


def test_logger_timestamp_is_iso8601_utc():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.info("hi")
    ts = captured[0].timestamp
    assert ts.endswith("Z")
    assert "T" in ts


def test_logger_metadata_passthrough():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.info("hi", metadata={"user_id": "123"})
    assert captured[0].metadata == {"user_id": "123"}


def test_logger_exc_info_attaches_stack_trace():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    try:
        raise ValueError("boom")
    except ValueError as e:
        log.error("crashed", exc_info=e)
    assert captured[0].stack_trace is not None
    assert "ValueError: boom" in captured[0].stack_trace


def test_logger_no_exc_info_no_stack_trace():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.error("plain error")
    assert captured[0].stack_trace is None
