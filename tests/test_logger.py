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


def test_logger_auto_generates_trace_id():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.info("hi")
    assert captured[0].trace_id is not None
    assert len(captured[0].trace_id) > 0


def test_logger_uses_provided_trace_id():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append, trace_id="my-trace-123")
    log.info("hi")
    assert captured[0].trace_id == "my-trace-123"


def test_logger_per_log_trace_id_override_via_metadata():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    log.info("hi", metadata={"traceId": "override-456", "extra": "data"})
    assert captured[0].trace_id == "override-456"
    assert captured[0].metadata == {"extra": "data"}
    assert "traceId" not in (captured[0].metadata or {})


def test_logger_get_and_set_trace_id():
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    original = log.get_trace_id()
    assert len(original) > 0
    log.set_trace_id("new-trace-789")
    assert log.get_trace_id() == "new-trace-789"
    log.info("hi")
    assert captured[0].trace_id == "new-trace-789"
