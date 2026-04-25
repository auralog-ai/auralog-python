# auralog

Python SDK for [Auralog](https://auralog.ai) — agentic logging and application awareness.

Auralog uses Claude as an on-call engineer: it monitors your logs and errors, alerts you when something's wrong, and opens fix PRs automatically.

[![PyPI version](https://img.shields.io/pypi/v/auralog.svg?label=pypi&color=blue)](https://pypi.org/project/auralog/)
[![provenance verified](https://img.shields.io/badge/provenance-verified-2dba4e?logo=sigstore&logoColor=white)](https://pypi.org/project/auralog/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/auralog/)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

## Install

```bash
pip install auralog
```

## Quick start

```python
from auralog import init, auralog

init(api_key="aura_your_key", environment="production")

auralog.info("user signed in", metadata={"user_id": "123"})
auralog.error("payment failed", metadata={"order_id": "abc"})
```

Python 3.10+.

## Bridge the stdlib `logging` module (recommended for existing codebases)

Python's `logging` module is used everywhere — including frameworks (Django, Flask, FastAPI) and libraries (requests, SQLAlchemy, Celery). `AuralogHandler` captures those logs without requiring code changes:

```python
import logging
from auralog import init, AuralogHandler

init(api_key="aura_your_key", environment="production")

logging.getLogger().addHandler(AuralogHandler())
logging.getLogger().setLevel(logging.INFO)

# Any existing logging.* calls — including from third-party libraries — flow to auralog
logging.info("payment processed", extra={"order_id": "abc"})
```

## Configuration

| Option | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | _required_ | Your Auralog project API key |
| `environment` | `str` | `"production"` | e.g. `"production"`, `"staging"`, `"dev"` |
| `endpoint` | `str` | `https://ingest.auralog.ai` | Ingest endpoint override |
| `flush_interval` | `float` | `5.0` | Seconds between batched flushes (errors flush immediately) |
| `capture_errors` | `bool` | `True` | Capture uncaught exceptions (main thread, threads, asyncio) |
| `trace_id` | `str` | _auto-generated_ | Custom trace ID for distributed tracing |
| `global_metadata` | `dict[str, Any]` or `Callable[[], dict[str, Any]]` | `None` | Baseline metadata merged into every emitted log entry. Per-call `metadata` keys win on collision (shallow merge). Synchronous suppliers only. |

## Attaching session-scoped fields to every log (`global_metadata`)

To pin fields like `user_id`, `tenant`, or a feature-flag snapshot onto **every** log entry — including framework-bridge captures (`AuralogHandler`) and uncaught-error captures — pass `global_metadata` to `init`. Two forms are supported:

**Static dict** — for values that don't change over the process lifetime:

```python
init(api_key="aura_your_key", global_metadata={"service": "billing", "region": "us-east"})
```

**Callable supplier** — invoked at every emit, so values can change over time. This is the canonical recipe for attaching the current user to every log:

```python
from contextvars import ContextVar
from auralog import init, auralog

current_user: ContextVar[str | None] = ContextVar("current_user", default=None)

def session_metadata() -> dict[str, object]:
    return {"user_id": current_user.get()}

init(api_key="aura_your_key", global_metadata=session_metadata)

# Anywhere a request handler sets the user, every subsequent log carries it:
current_user.set("u_123")
auralog.info("checkout completed")
# -> metadata = {"user_id": "u_123"}
```

Per-call metadata still wins on collision, so impersonation and admin actions can override:

```python
auralog.info("admin override", metadata={"user_id": "admin_7"})  # admin_7, not u_123
```

**Caveats:**
- The supplier runs on **every** emit — keep it O(1) cheap. Don't hit a database or do I/O.
- **Synchronous only.** If your supplier is an `async def`, or returns a coroutine/awaitable, the entry is emitted without `global_metadata` and a one-time warning is logged. Cache async state into a `ContextVar` or thread-local from the sync side.
- If the supplier raises, the entry is still emitted (without `global_metadata`) — logging never crashes the host.
- Non-JSON-serializable values are dropped (with a one-time warning); the entry still ships with per-call metadata.

## Attaching a traceback

```python
try:
    risky()
except Exception as e:
    auralog.error("task crashed", metadata={"task": "ingest"}, exc_info=e)
```

## Graceful shutdown

`auralog` flushes pending logs on interpreter exit automatically via `atexit`. For deterministic flush (serverless handlers, short-lived scripts):

```python
from auralog import shutdown
shutdown()
```

## Thread and async safety

- **Threads:** The transport uses a `threading.Lock` around the in-memory batch. Safe for multi-threaded apps (Django under Gunicorn, FastAPI workers, Celery).
- **Background flushing:** A daemon thread flushes every `flush_interval` seconds; errors send immediately on a separate endpoint.
- **Asyncio:** Error capture installs a handler on the active event loop when `init()` runs inside one. Call `init()` from your framework's startup hook so it installs against your app's loop.

## Verify this package

Every release is published with [sigstore provenance attestations](https://docs.pypi.org/trusted-publishers/) via GitHub Actions. The attestation proves the distribution was built from a specific commit in this repository — without having to trust PyPI or the maintainer.

Inspect the attestation on [pypi.org/project/auralog](https://pypi.org/project/auralog/) under "Provenance".

## Documentation

Full docs at [docs.auralog.ai](https://docs.auralog.ai/python-sdk/installation/).

## Security

Found a vulnerability? See [SECURITY.md](./SECURITY.md) for how to report it.

## License

[MIT](./LICENSE) © James Thomas
