"""
Automatic capture of uncaught exceptions across:
  - sys.excepthook (main thread)
  - threading.excepthook (other threads)
  - asyncio's default exception handler (running loops)

Designed to be idempotent and reversible (via uninstall_error_capture).
"""

from __future__ import annotations

import contextlib
import sys
import threading
from typing import Any

from .logger import Logger

_original_excepthook: Any = None
_original_threading_hook: Any = None


def install_error_capture(logger: Logger) -> None:
    """Install hooks. Safe to call multiple times — subsequent calls replace prior hooks."""
    global _original_excepthook, _original_threading_hook

    # Only capture the original ONCE so uninstall restores the actual default,
    # even if install is called multiple times.
    if _original_excepthook is None:
        _original_excepthook = sys.excepthook

    def _hook(exc_type: type[BaseException], exc_val: BaseException, exc_tb: Any) -> None:
        with contextlib.suppress(Exception):
            logger.error(f"Unhandled exception: {exc_val}", exc_info=exc_val)
        if _original_excepthook is not None:
            _original_excepthook(exc_type, exc_val, exc_tb)

    sys.excepthook = _hook

    if _original_threading_hook is None:
        _original_threading_hook = threading.excepthook

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        with contextlib.suppress(Exception):
            exc_val = args.exc_value
            thread_name = args.thread.name if args.thread else "?"
            logger.error(
                f"Unhandled exception in thread {thread_name}: {exc_val}",
                exc_info=exc_val if isinstance(exc_val, BaseException) else None,
            )
        if _original_threading_hook is not None:
            _original_threading_hook(args)

    threading.excepthook = _thread_hook

    # Asyncio: only wire up if there's a running loop. Don't create one
    # just to install a handler — that would surprise async-framework users.
    try:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            _install_asyncio_handler(loop, logger)
        except RuntimeError:
            pass
    except Exception:
        pass


def _install_asyncio_handler(loop: Any, logger: Logger) -> None:
    def _handler(_loop: Any, context: dict[str, Any]) -> None:
        exc = context.get("exception")
        msg = context.get("message", "asyncio error")
        try:
            if isinstance(exc, BaseException):
                logger.error(f"Asyncio error: {msg}", exc_info=exc)
            else:
                logger.error(f"Asyncio error: {msg}")
        except Exception:
            pass

    loop.set_exception_handler(_handler)


def uninstall_error_capture() -> None:
    """Restore the original excepthooks. Safe to call multiple times."""
    global _original_excepthook, _original_threading_hook
    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
        _original_excepthook = None
    if _original_threading_hook is not None:
        threading.excepthook = _original_threading_hook
        _original_threading_hook = None
