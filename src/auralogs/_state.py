"""
Module-level singleton state for the SDK, separated from `__init__` so the
handler can introspect it without circular imports.
"""

from __future__ import annotations

from .logger import Logger
from .transport import Transport

logger: Logger | None = None
transport: Transport | None = None
atexit_registered: bool = False
