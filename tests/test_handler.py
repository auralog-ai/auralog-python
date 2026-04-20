from __future__ import annotations

import logging

from auralog.handler import AuralogHandler
from auralog.logger import Logger
from auralog.types import LogEntry, LogLevel


def _make_handler_with_capture() -> tuple[AuralogHandler, list[LogEntry]]:
    captured: list[LogEntry] = []
    log = Logger(environment="prod", sink=captured.append)
    handler = AuralogHandler(logger=log)
    return handler, captured


def test_handler_maps_stdlib_levels_to_auralog_levels():
    handler, captured = _make_handler_with_capture()
    pylogger = logging.getLogger("test_handler_levels")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.DEBUG)

    pylogger.debug("d")
    pylogger.info("i")
    pylogger.warning("w")
    pylogger.error("e")
    pylogger.critical("c")

    levels = [e.level for e in captured]
    assert levels == [
        LogLevel.DEBUG,
        LogLevel.INFO,
        LogLevel.WARN,
        LogLevel.ERROR,
        LogLevel.FATAL,
    ]


def test_handler_forwards_message():
    handler, captured = _make_handler_with_capture()
    pylogger = logging.getLogger("test_handler_message")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)
    pylogger.info("hi")
    assert captured[0].message == "hi"


def test_handler_forwards_extra_as_metadata():
    handler, captured = _make_handler_with_capture()
    pylogger = logging.getLogger("test_handler_extra")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)
    pylogger.info("hi", extra={"user_id": "123", "tenant": "acme"})
    md = captured[0].metadata or {}
    assert md.get("user_id") == "123"
    assert md.get("tenant") == "acme"


def test_handler_captures_exception_stack():
    handler, captured = _make_handler_with_capture()
    pylogger = logging.getLogger("test_handler_exc")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)
    try:
        raise ValueError("boom")
    except ValueError:
        pylogger.exception("crashed")
    assert captured[0].stack_trace is not None
    assert "ValueError: boom" in captured[0].stack_trace


def test_handler_silently_drops_when_uninitialized():
    """If the global logger is None, emit should not raise."""
    handler = AuralogHandler()  # no explicit logger
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hi",
        args=None,
        exc_info=None,
    )
    handler.emit(record)  # must not raise


def test_handler_does_not_leak_reserved_logrecord_fields_into_metadata():
    handler, captured = _make_handler_with_capture()
    pylogger = logging.getLogger("test_handler_reserved")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)
    pylogger.info("hi", extra={"custom": "yes"})
    md = captured[0].metadata or {}
    assert "custom" in md
    for reserved in ("message", "asctime", "levelname", "name"):
        assert reserved not in md
