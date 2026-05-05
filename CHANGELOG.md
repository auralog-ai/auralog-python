# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- **Bounded in-memory buffer.** New `max_queue_size` config option (default `1000`). When the buffer would exceed this size the oldest entries are dropped first, so an unreachable ingest endpoint can no longer OOM the host process.
- **HTTPS-only endpoints by default.** `AuralogConfig` now rejects an `endpoint` that doesn't start with `https://`. Pass `allow_insecure_endpoint=True` to opt in (e.g. for a local development ingest). Previously a misconfigured `endpoint=http://...` silently downgraded every POST to plaintext.
- **Optional `metadata_allowlist` on `AuralogHandler`.** When set, only the named keys from `LogRecord.__dict__` are forwarded; default denylist behavior is preserved when it is omitted. Closes the gap where `extra={"auth_token": ...}` would flow into the wire payload because the denylist couldn't anticipate every host-side attribute name.

## [0.2.0] - 2026-04-25

### Added
- `global_metadata` config field on `init()`: a baseline metadata map merged into every emitted log entry. Accepts either a static `dict[str, Any]` or a zero-arg `Callable[[], dict[str, Any]]` supplier (invoked at every emit for late binding — e.g. `lambda: {"user_id": current_user.get()}`). Per-call `metadata` keys win on collision (shallow merge). Synchronous only — coroutine/awaitable returns are treated as failure and the entry ships without `global_metadata`.
- `AuralogHandler`-emitted entries (stdlib `logging` bridge) now carry merged metadata. Previously they only carried per-call `extra={...}`; with `global_metadata` configured they now also pick up session-scoped fields.
- Uncaught-error capture entries (`sys.excepthook`, `threading.excepthook`, asyncio default handler) now carry `global_metadata` too.

### Changed
- Internal SDK warnings (e.g. misbehaving `global_metadata` supplier) are now routed through the `auralog` stdlib logger at `WARNING`. Failures of the same kind are emitted once per `Logger` instance — subsequent failures are silent.

### Compatibility
- Fully backward compatible. Absent `global_metadata`, behavior is unchanged.

## [0.1.0] - 2026-04-20

### Added
- Initial release.
- Core SDK: `init`, `shutdown`, `auralog.debug/info/warn/error/fatal`.
- `AuralogHandler` for stdlib `logging` integration.
- Automatic error capture via `sys.excepthook`, `threading.excepthook`, and asyncio exception handler (opt-out via `capture_errors=False`).
- Thread-safe batched HTTP transport over `httpx` with daemon background flushing.
- Graceful shutdown via `atexit` (auto-registered in `init`).
