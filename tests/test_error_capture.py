from __future__ import annotations

import sys
import threading

from auralog.error_capture import install_error_capture, uninstall_error_capture
from auralog.logger import Logger
from auralog.types import LogEntry


def test_excepthook_captures_uncaught_main_thread():
    captured: list[LogEntry] = []
    log = Logger(environment="test", sink=captured.append)
    install_error_capture(log)
    try:
        try:
            raise ValueError("main-uncaught")
        except ValueError:
            exc_type, exc_val, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_val, exc_tb)
    finally:
        uninstall_error_capture()

    assert any("main-uncaught" in (e.stack_trace or "") for e in captured)


def test_threading_excepthook_captures():
    captured: list[LogEntry] = []
    log = Logger(environment="test", sink=captured.append)
    install_error_capture(log)
    try:

        def boom():
            raise RuntimeError("thread-boom")

        th = threading.Thread(target=boom)
        th.start()
        th.join()
    finally:
        uninstall_error_capture()

    assert any("thread-boom" in (e.stack_trace or "") for e in captured)


def test_uninstall_restores_original_hooks():
    log = Logger(environment="test", sink=lambda _: None)
    original_sys_hook = sys.excepthook
    original_thread_hook = threading.excepthook

    install_error_capture(log)
    assert sys.excepthook is not original_sys_hook
    assert threading.excepthook is not original_thread_hook

    uninstall_error_capture()
    assert sys.excepthook is original_sys_hook
    assert threading.excepthook is original_thread_hook


def test_install_is_idempotent():
    """Calling install twice should not double-wrap the original hook."""
    captured: list[LogEntry] = []
    log = Logger(environment="test", sink=captured.append)
    original_sys_hook = sys.excepthook

    install_error_capture(log)
    install_error_capture(log)

    uninstall_error_capture()
    assert sys.excepthook is original_sys_hook
