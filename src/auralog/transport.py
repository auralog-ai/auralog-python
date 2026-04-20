from __future__ import annotations

import contextlib
import threading

import httpx

from .types import LogEntry, LogLevel, is_at_or_above


class Transport:
    """
    Thread-safe batched HTTP transport.

    - Buffers non-error logs; a daemon background thread flushes every `flush_interval`.
    - Errors (`LogLevel.ERROR` and above) are sent immediately on a separate endpoint.
    - Network failures are swallowed so a log send never crashes the host app.
    """

    def __init__(self, *, api_key: str, endpoint: str, flush_interval: float) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._flush_interval = flush_interval
        self._buffer: list[LogEntry] = []
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=5.0)
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_background()

    def _start_background(self) -> None:
        self._thread = threading.Thread(
            target=self._run,
            name="auralog-flush",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        # Never let the background thread die on a transient failure — a bad
        # network blip shouldn't bring down log batching.
        while not self._stopped.wait(self._flush_interval):
            with contextlib.suppress(Exception):
                self.flush()

    def send(self, entry: LogEntry) -> None:
        if is_at_or_above(entry.level, LogLevel.ERROR):
            self._send_single(entry)
            return
        with self._lock:
            self._buffer.append(entry)

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer
            self._buffer = []
        # Swallow network blips so a single send failure doesn't crash the host.
        with contextlib.suppress(Exception):
            self._client.post(
                f"{self._endpoint}/v1/logs",
                json={
                    "projectApiKey": self._api_key,
                    "logs": [e.to_wire() for e in batch],
                },
            )

    def _send_single(self, entry: LogEntry) -> None:
        with contextlib.suppress(Exception):
            self._client.post(
                f"{self._endpoint}/v1/logs/single",
                json={"projectApiKey": self._api_key, "log": entry.to_wire()},
            )

    def shutdown(self) -> None:
        self._stopped.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.flush()
        self._client.close()
