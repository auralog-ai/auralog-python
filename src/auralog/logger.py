from __future__ import annotations

import contextlib
import inspect
import json
import logging
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .config import GlobalMetadata
from .types import LogEntry, LogLevel

# Channel for internal SDK complaints. Kept separate from the user's root
# logger so a misconfigured `global_metadata` supplier doesn't muddy app logs.
_internal_logger = logging.getLogger("auralog")


class Logger:
    """
    Emits structured log entries to a sink callable (typically Transport.send).

    Separating the logger from the transport makes both easier to test
    and keeps a clean boundary between "what to log" and "how to send".
    """

    def __init__(
        self,
        *,
        environment: str,
        sink: Callable[[LogEntry], None],
        trace_id: str | None = None,
        global_metadata: GlobalMetadata | None = None,
    ) -> None:
        self._environment = environment
        self._sink = sink
        self._trace_id = trace_id if trace_id is not None else str(uuid.uuid4())
        self._global_metadata: GlobalMetadata | None = global_metadata
        # Tracks whether we've already emitted a warning about a misbehaving
        # supplier (raise / async return / non-serializable result). Per-instance
        # so re-init resets the flag.
        self._global_metadata_warned: bool = False

    def get_trace_id(self) -> str:
        return self._trace_id

    def set_trace_id(self, trace_id: str) -> None:
        self._trace_id = trace_id

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _warn_once(self, message: str) -> None:
        if self._global_metadata_warned:
            return
        self._global_metadata_warned = True
        _internal_logger.warning("auralog: %s", message)

    def _resolve_global_metadata(self) -> dict[str, Any] | None:
        """
        Resolve the configured global_metadata to a concrete dict, or None
        if unset / failed. Failure modes (per spec):
          - supplier raises -> warn-once, return None
          - supplier returns awaitable/coroutine -> warn-once, return None
        """
        source = self._global_metadata
        if source is None:
            return None

        if callable(source):
            # Reject coroutine functions before invocation — we don't even
            # want to call them, since calling produces an un-awaited coroutine
            # that will later trigger a "coroutine was never awaited" warning.
            if inspect.iscoroutinefunction(source):
                self._warn_once(
                    "global_metadata supplier is async; returning entry without "
                    "global_metadata. Cache async state synchronously instead."
                )
                return None
            try:
                resolved: Any = source()
            except Exception as supplier_error:
                self._warn_once(
                    "global_metadata supplier raised "
                    f"{type(supplier_error).__name__}: {supplier_error}; "
                    "returning entry without global_metadata."
                )
                return None
            if inspect.iscoroutine(resolved) or inspect.isawaitable(resolved):
                # Close the coroutine to suppress the "never awaited" warning.
                close = getattr(resolved, "close", None)
                if callable(close):
                    with contextlib.suppress(Exception):
                        close()
                self._warn_once(
                    "global_metadata supplier returned an awaitable/coroutine; "
                    "returning entry without global_metadata. Synchronous suppliers only."
                )
                return None
            if not isinstance(resolved, dict):
                self._warn_once(
                    "global_metadata supplier returned non-dict "
                    f"({type(resolved).__name__}); returning entry without global_metadata."
                )
                return None
            return resolved

        # Static dict form. Return as-is (shallow merge will copy below).
        if isinstance(source, dict):
            return source

        self._warn_once(
            f"global_metadata is of unsupported type {type(source).__name__}; "
            "expected dict or callable returning dict."
        )
        return None

    def _build_metadata(self, per_call: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Shallow-merge resolved global_metadata with per-call metadata
        (per-call wins on key collision). Apply serialization defense:
        if the merged dict is not JSON-serializable, drop the global side
        and warn once. Returns None if both sides are empty/absent.
        """
        global_meta = self._resolve_global_metadata()

        if global_meta is None and per_call is None:
            return None
        if global_meta is None:
            # Copy so callers can't mutate the original later.
            return dict(per_call) if per_call else None
        # Shallow merge — per-call wins on collision.
        merged = dict(global_meta) if per_call is None else {**global_meta, **per_call}

        # Serialization defense: ensure the merged dict will survive the
        # transport's JSON encoder. If not, drop global_metadata for this
        # entry but keep per-call (which presumably worked before).
        try:
            json.dumps(merged)
        except (TypeError, ValueError) as serialization_error:
            self._warn_once(
                "global_metadata produced a non-JSON-serializable value "
                f"({type(serialization_error).__name__}: {serialization_error}); "
                "dropping global_metadata for this entry."
            )
            return dict(per_call) if per_call else None

        return merged

    def _emit(
        self,
        level: LogLevel,
        message: str,
        metadata: dict[str, Any] | None,
        exc_info: BaseException | None,
    ) -> None:
        stack: str | None = None
        if exc_info is not None:
            stack = "".join(
                traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)
            )

        merged_meta = self._build_metadata(metadata)

        entry_trace_id = self._trace_id
        clean_meta = merged_meta
        if merged_meta is not None and "traceId" in merged_meta:
            entry_trace_id = str(merged_meta["traceId"])
            clean_meta = {key: value for key, value in merged_meta.items() if key != "traceId"}
            if not clean_meta:
                clean_meta = None

        self._sink(
            LogEntry(
                level=level,
                message=message,
                environment=self._environment,
                timestamp=self._now(),
                metadata=clean_meta,
                stack_trace=stack,
                trace_id=entry_trace_id,
            )
        )

    def debug(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.DEBUG, message, metadata, None)

    def info(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.INFO, message, metadata, None)

    def warn(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.WARN, message, metadata, None)

    def error(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._emit(LogLevel.ERROR, message, metadata, exc_info)

    def fatal(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        exc_info: BaseException | None = None,
    ) -> None:
        self._emit(LogLevel.FATAL, message, metadata, exc_info)
