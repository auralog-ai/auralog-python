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
    # Workers push 10 * 200 = 2000 entries; bump the cap above the default
    # 1000 so this test exercises buffer integrity, not eviction.
    t = Transport(api_key="k", endpoint="http://fake", flush_interval=60.0, max_queue_size=5000)

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


def test_buffer_drops_oldest_when_capped(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs", method="POST", status_code=200)
    transport = Transport(
        api_key="k", endpoint="http://fake", flush_interval=60.0, max_queue_size=3
    )
    # Push 5 entries into a buffer that holds 3 — the oldest two ("0" and "1")
    # must be evicted.
    for index in range(5):
        transport.send(_entry(LogLevel.INFO, str(index)))

    transport.flush()
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    body = json.loads(requests[0].read().decode())
    messages = [log["message"] for log in body["logs"]]
    assert messages == ["2", "3", "4"]
    transport.shutdown()


def test_endpoint_trailing_slash_is_stripped(httpx_mock):
    httpx_mock.add_response(url="http://fake/v1/logs/single", method="POST", status_code=200)
    t = Transport(api_key="k", endpoint="http://fake/", flush_interval=60.0)
    t.send(_entry(LogLevel.ERROR, "boom"))
    t.shutdown()
    reqs = httpx_mock.get_requests()
    assert reqs[0].url.path == "/v1/logs/single"
