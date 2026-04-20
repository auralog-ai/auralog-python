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
