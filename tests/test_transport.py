from __future__ import annotations

import json
import threading

import httpx

from auralog.transport import Transport
from auralog.types import LogEntry, LogLevel


def _entry(level: LogLevel = LogLevel.INFO, message: str = "m") -> LogEntry:
    return LogEntry(
        level=level,
        message=message,
        environment="test",
        timestamp="2026-04-20T00:00:00Z",
    )


def test_send_below_error_is_buffered(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0)
    t.send(_entry(LogLevel.INFO, "hi"))
    assert len(httpx_mock.get_requests()) == 0
    t.flush()
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 1
    assert reqs[0].url.path == "/v1/logs"
    t.shutdown()


def test_error_level_sends_single_immediately(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs/single", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0)
    t.send(_entry(LogLevel.ERROR, "boom"))
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 1
    assert reqs[0].url.path == "/v1/logs/single"
    t.shutdown()


def test_network_error_is_swallowed(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("bad"), url="http://fake/v1/logs", method="POST")
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0)
    t.send(_entry(LogLevel.INFO, "hi"))
    t.flush()  # must not raise
    t.shutdown()


def test_concurrent_send_does_not_corrupt_buffer(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0)

    def worker():
        for _ in range(200):
            t.send(_entry(LogLevel.INFO, "x"))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    t.flush()
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 1
    body = reqs[0].read().decode()
    assert len(json.loads(body)["logs"]) == 2000
    t.shutdown()


def test_shutdown_flushes_pending(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0)
    t.send(_entry(LogLevel.INFO, "hi"))
    t.shutdown()
    assert len(httpx_mock.get_requests()) == 1


def test_endpoint_trailing_slash_is_stripped(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs/single", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake/", flush_interval=60.0)
    t.send(_entry(LogLevel.ERROR, "boom"))
    t.shutdown()
    reqs = httpx_mock.get_requests()
    assert reqs[0].url.path == "/v1/logs/single"
