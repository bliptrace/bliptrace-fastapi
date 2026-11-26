# bliptrace-fastapi

FastAPI / Starlette adapter for [Bliptrace](https://scope.g8suite.com) — the
central, runtime-agnostic error-capture and observability platform.

This is a **thin** adapter over the runtime [`bliptrace`](../bliptrace-python) Python
SDK. It adds an ASGI middleware that captures unhandled exceptions from your
FastAPI (or any Starlette) application, enriches them with request context, ships
them to the Bliptrace ingest API — and then re-raises so your app's normal error
handling continues unchanged.

**Capturing never breaks the host app.** Every step on the capture path is
guarded; a slow or broken ingest path never affects your responses.

## Installation

The runtime SDK `bliptrace` is currently unpublished, so install it as an editable
local dependency first:

```bash
python3 -m pip install --user -e ../bliptrace-python
python3 -m pip install --user -e .          # this adapter
python3 -m pip install --user fastapi        # if not already present
```

## Usage

### Middleware (recommended)

```python
from fastapi import FastAPI
from bliptrace_fastapi import BliptraceMiddleware

app = FastAPI()
app.add_middleware(
    BliptraceMiddleware,
    key="your-ingest-key",
    environment="production",
)
```

### Helper

```python
from bliptrace_fastapi import add_bliptrace

add_bliptrace(app, key="your-ingest-key", environment="production")
```

### Exception-handler variant

If you prefer an explicit handler over middleware:

```python
from bliptrace import Client, Config
from bliptrace_fastapi import bliptrace_exception_handler

client = Client(Config(key="your-ingest-key"))
app.add_exception_handler(Exception, bliptrace_exception_handler(client))
```

## Configuration

All keyword arguments to `BliptraceMiddleware` / `add_bliptrace` (other than the
internal `client`) are forwarded to `bliptrace.Config`:

| Option | Default | Description |
|---|---|---|
| `key` | `None` | Ingest key. Nothing is sent without it. |
| `endpoint` | `https://ingest.scope.g8suite.com` | Ingest API base URL. |
| `environment` | `production` | Deployment environment label. |
| `release` | `None` | Release / version identifier. |
| `base_path` | `""` | App root path, used for in-app frame detection. |
| `enabled` | `True` | Master switch. |
| `ignore_exceptions` | `[]` | Exception classes or names to skip. |
| `scrub_keys` | `[]` | Extra context keys to redact. |
| `timeout` | `3` | Ingest request timeout (seconds). |

### What is sent

The error envelope carries the runtime, SDK, exception type/message/frames, and
request context (method, URL, and headers with `authorization` and `cookie`
stripped). The **project is never sent** — the ingest API resolves it
server-side from the ingest key (anti-spoof). PII is scrubbed before anything
leaves the process.

## Testing

```bash
python3 -m pip install --user -e ../bliptrace-python
python3 -m pip install --user pytest fastapi httpx
python3 -m pytest -q
```

## Licence

MIT — Developers Hub Sdn Bhd. See [LICENSE](LICENSE).
