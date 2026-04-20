# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added
- Initial release.
- Core SDK: `init`, `shutdown`, `auralog.debug/info/warn/error/fatal`.
- `AuralogHandler` for stdlib `logging` integration.
- Automatic error capture via `sys.excepthook`, `threading.excepthook`, and asyncio exception handler (opt-out via `capture_errors=False`).
- Thread-safe batched HTTP transport over `httpx` with daemon background flushing.
- Graceful shutdown via `atexit` (auto-registered in `init`).
