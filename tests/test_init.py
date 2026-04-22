from __future__ import annotations

import pytest

import auralog as al
from auralog import get_trace_id, set_trace_id


def test_auralog_before_init_raises():
    al.shutdown()
    with pytest.raises(RuntimeError, match="init"):
        al.auralog.info("hi")


def test_init_enables_logging(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    httpx_mock.add_response(url="http://fake/v1/logs/single", method="POST", status_code=200)

    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake",
        flush_interval=60.0,
        capture_errors=False,
    )
    try:
        al.auralog.info("hi")
        al.auralog.error("boom")
    finally:
        al.shutdown()

    # There should be at least one request for the batch (info) and one for the error.
    paths = [r.url.path for r in httpx_mock.get_requests()]
    assert "/v1/logs/single" in paths


def test_second_init_replaces_previous(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    httpx_mock.add_response(url="http://fake2/v1/logs", method="POST", status_code=200)

    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake",
        flush_interval=60.0,
        capture_errors=False,
    )
    al.auralog.info("first")

    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake2",
        flush_interval=60.0,
        capture_errors=False,
    )
    al.auralog.info("second")

    al.shutdown()

    paths = [r.url for r in httpx_mock.get_requests()]
    hosts = {u.host for u in paths}
    # Both endpoints should have been hit (first flushed on shutdown-within-init,
    # second flushed on final shutdown).
    assert "fake" in hosts and "fake2" in hosts


def test_get_trace_id_returns_uuid_after_init(httpx_mock):
    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake",
        flush_interval=60.0,
        capture_errors=False,
    )
    try:
        tid = get_trace_id()
        assert isinstance(tid, str)
        assert len(tid) > 0
    finally:
        al.shutdown()


def test_set_trace_id_changes_trace_id(httpx_mock):
    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake",
        flush_interval=60.0,
        capture_errors=False,
    )
    try:
        set_trace_id("custom-trace")
        assert get_trace_id() == "custom-trace"
    finally:
        al.shutdown()


def test_get_trace_id_throws_before_init():
    al.shutdown()
    with pytest.raises(RuntimeError, match="init"):
        get_trace_id()


def test_trace_id_from_config(httpx_mock):
    al.init(
        api_key="k",
        environment="test",
        endpoint="http://fake",
        flush_interval=60.0,
        capture_errors=False,
        trace_id="config-trace-123",
    )
    try:
        assert get_trace_id() == "config-trace-123"
    finally:
        al.shutdown()
