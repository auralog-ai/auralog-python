"""
Tests for the `global_metadata` config field and its merge semantics.

Covers the eight cases mandated by the cross-SDK spec:
  1. Static map form attaches to every entry.
  2. Supplier form is invoked per emission.
  3. Supplier that throws -> entry without global_metadata + one warn.
  4. Supplier returns awaitable/coroutine -> entry without global_metadata + warn.
  5. Per-call key overrides a global_metadata key on collision.
  6. Framework-bridge-produced entries (AuralogHandler) carry global_metadata.
  7. Error-capture-produced entries carry global_metadata.
  8. Non-serializable return value -> entry without global_metadata + warn,
     entry still delivered.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from auralog.error_capture import install_error_capture, uninstall_error_capture
from auralog.handler import AuralogHandler
from auralog.logger import Logger
from auralog.types import LogEntry


def _make_logger(global_metadata: Any = None) -> tuple[Logger, list[LogEntry]]:
    captured: list[LogEntry] = []
    log = Logger(
        environment="test",
        sink=captured.append,
        global_metadata=global_metadata,
    )
    return log, captured


# ---------------------------------------------------------------------------
# 1. Static map form
# ---------------------------------------------------------------------------


def test_static_global_metadata_attaches_to_every_entry():
    log, captured = _make_logger(global_metadata={"user_id": "u1", "tenant": "acme"})
    log.info("first")
    log.warn("second")
    log.error("third")

    assert len(captured) == 3
    for entry in captured:
        assert entry.metadata is not None
        assert entry.metadata["user_id"] == "u1"
        assert entry.metadata["tenant"] == "acme"


def test_no_global_metadata_no_change_in_behavior():
    log, captured = _make_logger(global_metadata=None)
    log.info("hi")
    assert captured[0].metadata is None


def test_static_global_metadata_merges_with_per_call():
    log, captured = _make_logger(global_metadata={"user_id": "u1"})
    log.info("hi", metadata={"order_id": "o1"})
    assert captured[0].metadata == {"user_id": "u1", "order_id": "o1"}


# ---------------------------------------------------------------------------
# 2. Supplier form invoked per emission
# ---------------------------------------------------------------------------


def test_supplier_invoked_on_every_emit():
    call_count = {"n": 0}

    def supplier() -> dict[str, Any]:
        call_count["n"] += 1
        return {"call": call_count["n"]}

    log, captured = _make_logger(global_metadata=supplier)
    log.info("a")
    log.info("b")
    log.info("c")

    assert call_count["n"] == 3
    assert captured[0].metadata == {"call": 1}
    assert captured[1].metadata == {"call": 2}
    assert captured[2].metadata == {"call": 3}


def test_supplier_late_binds_user_id():
    """Canonical 'attach user_id to every log' recipe."""
    state = {"user_id": "alice"}
    log, captured = _make_logger(global_metadata=lambda: {"user_id": state["user_id"]})

    log.info("first")
    state["user_id"] = "bob"
    log.info("second")

    assert captured[0].metadata == {"user_id": "alice"}
    assert captured[1].metadata == {"user_id": "bob"}


# ---------------------------------------------------------------------------
# 3. Supplier raises -> entry without global_metadata + one warn
# ---------------------------------------------------------------------------


def test_supplier_raise_emits_entry_without_global_metadata(caplog):
    def bad_supplier() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    log, captured = _make_logger(global_metadata=bad_supplier)

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log.info("first")
        log.info("second", metadata={"x": 1})

    # Entries are still delivered.
    assert len(captured) == 2
    # Global metadata is absent, per-call survives.
    assert captured[0].metadata is None
    assert captured[1].metadata == {"x": 1}

    # Exactly one warn across the two failures.
    auralog_warnings = [r for r in caplog.records if r.name == "auralog"]
    assert len(auralog_warnings) == 1
    assert "supplier raised" in auralog_warnings[0].getMessage()


def test_supplier_raise_does_not_crash_host():
    """Per the spec: logging must never crash the host application."""

    def bad_supplier() -> dict[str, Any]:
        raise ValueError("nope")

    log, captured = _make_logger(global_metadata=bad_supplier)
    # Must not raise.
    log.info("ok")
    log.error("still ok")
    assert len(captured) == 2


# ---------------------------------------------------------------------------
# 4. Supplier returns awaitable/coroutine -> entry without global + warn
# ---------------------------------------------------------------------------


def test_async_supplier_function_treated_as_failure(caplog):
    async def async_supplier() -> dict[str, Any]:
        return {"user_id": "u1"}

    log, captured = _make_logger(global_metadata=async_supplier)

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log.info("hi")
        log.info("again")

    assert captured[0].metadata is None
    assert captured[1].metadata is None
    auralog_warnings = [r for r in caplog.records if r.name == "auralog"]
    assert len(auralog_warnings) == 1
    assert "async" in auralog_warnings[0].getMessage().lower()


def test_supplier_returning_coroutine_treated_as_failure(caplog):
    async def _coro() -> dict[str, Any]:
        return {"user_id": "u1"}

    def returns_coroutine() -> Any:
        # A non-async function that produces a coroutine object — still
        # awaitable, must be rejected and never awaited.
        return _coro()

    log, captured = _make_logger(global_metadata=returns_coroutine)

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log.info("hi")

    assert captured[0].metadata is None
    auralog_warnings = [r for r in caplog.records if r.name == "auralog"]
    assert len(auralog_warnings) == 1
    assert (
        "awaitable" in auralog_warnings[0].getMessage().lower()
        or "coroutine" in auralog_warnings[0].getMessage().lower()
    )


# ---------------------------------------------------------------------------
# 5. Per-call wins on collision
# ---------------------------------------------------------------------------


def test_per_call_key_overrides_global_key_on_collision():
    log, captured = _make_logger(global_metadata={"user_id": "default-user", "tenant": "acme"})
    log.info("admin action", metadata={"user_id": "admin-7"})

    assert captured[0].metadata == {"user_id": "admin-7", "tenant": "acme"}


def test_shallow_merge_replaces_nested_value_wholesale():
    """Shallow only — per-call replaces the whole value at a colliding key."""
    log, captured = _make_logger(
        global_metadata={"context": {"feature_a": True, "feature_b": False}}
    )
    log.info("hi", metadata={"context": {"feature_a": False}})

    # Shallow merge: per-call's `context` replaces global's `context` entirely.
    assert captured[0].metadata == {"context": {"feature_a": False}}


# ---------------------------------------------------------------------------
# 6. Framework-bridge (AuralogHandler) entries carry global_metadata
# ---------------------------------------------------------------------------


def test_handler_emitted_entries_carry_global_metadata():
    log, captured = _make_logger(global_metadata=lambda: {"user_id": "u1"})
    handler = AuralogHandler(logger=log)
    pylogger = logging.getLogger("test_handler_global_metadata")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)

    pylogger.info("through stdlib", extra={"order_id": "o1"})

    assert captured[0].metadata is not None
    assert captured[0].metadata["user_id"] == "u1"  # from global_metadata
    assert captured[0].metadata["order_id"] == "o1"  # from per-call extra


def test_handler_emitted_entry_with_no_extra_still_carries_global():
    log, captured = _make_logger(global_metadata={"user_id": "u1"})
    handler = AuralogHandler(logger=log)
    pylogger = logging.getLogger("test_handler_global_only")
    pylogger.handlers = [handler]
    pylogger.setLevel(logging.INFO)

    pylogger.info("no extra")

    assert captured[0].metadata is not None
    assert captured[0].metadata["user_id"] == "u1"


# ---------------------------------------------------------------------------
# 7. Error-capture entries carry global_metadata
# ---------------------------------------------------------------------------


def test_error_capture_entries_carry_global_metadata():
    log, captured = _make_logger(global_metadata=lambda: {"user_id": "u1"})
    install_error_capture(log)
    try:
        try:
            raise ValueError("captured-uncaught")
        except ValueError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_val, exc_tb)
    finally:
        uninstall_error_capture()

    relevant = [e for e in captured if "captured-uncaught" in (e.stack_trace or "")]
    assert relevant, "expected error_capture to deliver an entry"
    assert relevant[0].metadata is not None
    assert relevant[0].metadata["user_id"] == "u1"


# ---------------------------------------------------------------------------
# 8. Non-serializable return -> entry without global_metadata + warn
# ---------------------------------------------------------------------------


def test_non_serializable_global_metadata_drops_global_keeps_per_call(caplog):
    class NotSerializable:
        pass

    log, captured = _make_logger(
        global_metadata=lambda: {"obj": NotSerializable(), "user_id": "u1"}
    )

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log.info("first", metadata={"order_id": "o1"})
        log.info("second")

    # Both entries delivered.
    assert len(captured) == 2
    # global_metadata dropped on both; per-call survives on the first.
    assert captured[0].metadata == {"order_id": "o1"}
    assert captured[1].metadata is None

    auralog_warnings = [r for r in caplog.records if r.name == "auralog"]
    assert len(auralog_warnings) == 1
    assert "serializable" in auralog_warnings[0].getMessage().lower()


def test_non_serializable_with_no_per_call_omits_metadata_entirely(caplog):
    class NotSerializable:
        pass

    log, captured = _make_logger(global_metadata={"obj": NotSerializable()})

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log.info("hi")

    # Per spec: both sides empty (per-call absent + global dropped) -> omit.
    assert captured[0].metadata is None


# ---------------------------------------------------------------------------
# Cross-cutting: warn-once flag is per-instance and silent thereafter
# ---------------------------------------------------------------------------


def test_warn_once_flag_is_per_instance(caplog):
    def bad_supplier() -> dict[str, Any]:
        raise RuntimeError("nope")

    log_a, _ = _make_logger(global_metadata=bad_supplier)
    log_b, _ = _make_logger(global_metadata=bad_supplier)

    with caplog.at_level(logging.WARNING, logger="auralog"):
        log_a.info("a1")
        log_a.info("a2")  # silent
        log_b.info("b1")  # separate instance — should warn once
        log_b.info("b2")  # silent

    auralog_warnings = [r for r in caplog.records if r.name == "auralog"]
    assert len(auralog_warnings) == 2


# ---------------------------------------------------------------------------
# traceId override still works when global_metadata is present
# ---------------------------------------------------------------------------


def test_per_call_traceid_still_overrides_with_global_metadata():
    log, captured = _make_logger(global_metadata={"user_id": "u1"})
    log.info("hi", metadata={"traceId": "trace-from-call"})
    assert captured[0].trace_id == "trace-from-call"
    # traceId was stripped from metadata; global_metadata user_id remains.
    assert captured[0].metadata == {"user_id": "u1"}
