from auralog.types import LogEntry, LogLevel, is_at_or_above


def test_log_level_ordering():
    assert is_at_or_above(LogLevel.ERROR, LogLevel.WARN)
    assert is_at_or_above(LogLevel.FATAL, LogLevel.ERROR)
    assert not is_at_or_above(LogLevel.DEBUG, LogLevel.INFO)
    assert is_at_or_above(LogLevel.INFO, LogLevel.INFO)


def test_log_entry_to_wire_omits_empty_fields():
    entry = LogEntry(
        level=LogLevel.INFO,
        message="hi",
        environment="prod",
        timestamp="2026-04-20T00:00:00Z",
    )
    wire = entry.to_wire()
    assert wire == {
        "level": "info",
        "message": "hi",
        "environment": "prod",
        "timestamp": "2026-04-20T00:00:00Z",
    }


def test_log_entry_to_wire_includes_metadata_and_stack():
    entry = LogEntry(
        level=LogLevel.ERROR,
        message="boom",
        environment="prod",
        timestamp="2026-04-20T00:00:00Z",
        metadata={"user_id": "123"},
        stack_trace="Traceback...",
    )
    wire = entry.to_wire()
    assert wire["level"] == "error"
    assert wire["metadata"] == {"user_id": "123"}
    assert wire["stackTrace"] == "Traceback..."


def test_log_entry_to_wire_includes_trace_id():
    entry = LogEntry(
        level=LogLevel.INFO,
        message="hi",
        environment="prod",
        timestamp="2026-04-20T00:00:00Z",
        trace_id="trace-abc",
    )
    wire = entry.to_wire()
    assert wire["traceId"] == "trace-abc"


def test_log_entry_to_wire_omits_trace_id_when_none():
    entry = LogEntry(
        level=LogLevel.INFO,
        message="hi",
        environment="prod",
        timestamp="2026-04-20T00:00:00Z",
    )
    wire = entry.to_wire()
    assert "traceId" not in wire
