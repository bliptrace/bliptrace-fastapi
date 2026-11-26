"""FastAPI/Starlette glue over the Bliptrace Python SDK.

A thin :class:`~starlette.middleware.base.BaseHTTPMiddleware` that wraps the
downstream handler, captures any unhandled exception via the runtime SDK, and
re-raises so FastAPI's normal error handling continues unchanged.

Design rule (from the Bliptrace spec): capturing must NEVER break the host app.
Every step on the capture path is guarded; a failure there is swallowed and the
original exception always propagates.

``project`` is never sent — the ingest API resolves the project server-side
from the ingest ``key`` (anti-spoof).
"""

from __future__ import annotations

from typing import Any, Optional

from bliptrace import Client, Config

from .context import request_context

try:  # Starlette is an optional/runtime dependency of the host app.
    from starlette.middleware.base import BaseHTTPMiddleware

    _BASE = BaseHTTPMiddleware
except Exception:  # pragma: no cover - exercised only without starlette
    _BASE = object  # type: ignore[assignment,misc]


def _build_client(client: Optional[Client], **config: Any) -> Client:
    """Build a Client from kwargs, or pass an explicit one through (for tests)."""
    if client is not None:
        return client
    return Client(Config(**config))


class BliptraceMiddleware(_BASE):  # type: ignore[misc,valid-type]
    """Capture unhandled exceptions from FastAPI/Starlette requests.

    Register with::

        app.add_middleware(BliptraceMiddleware, key="ingest-key", environment="production")

    The ``client`` keyword accepts a pre-built :class:`bliptrace.Client` (used by
    tests with a fake transport). Any other keyword is forwarded to
    :class:`bliptrace.Config`.
    """

    def __init__(
        self, app: Any, client: Optional[Client] = None, **config: Any
    ) -> None:
        super().__init__(app)
        self._client = _build_client(client, **config)

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        try:
            return await call_next(request)
        except Exception as exc:
            self._capture(exc, request)
            raise  # never mask the host app's error handling

    def _capture(self, exc: BaseException, request: Any) -> None:
        # Belt-and-braces: the SDK is already guarded, but never let the
        # capture path itself raise into the host request.
        try:
            self._client.capture(exc, request_context(request))
        except Exception:
            pass


def add_bliptrace(app: Any, client: Optional[Client] = None, **config: Any) -> None:
    """Convenience helper: ``add_bliptrace(app, key="...")``.

    Equivalent to ``app.add_middleware(BliptraceMiddleware, key="...")``.
    """
    app.add_middleware(BliptraceMiddleware, client=client, **config)


def bliptrace_exception_handler(client: Client) -> Any:
    """Build a FastAPI exception handler variant.

    Some apps prefer an explicit handler over middleware. Register with::

        client = Client(Config(key="..."))
        app.add_exception_handler(Exception, bliptrace_exception_handler(client))

    The handler captures, then re-raises so FastAPI's default 500 handling runs.
    Capture is fully guarded and never masks the original exception.
    """

    async def handler(request: Any, exc: BaseException) -> Any:
        try:
            client.capture(exc, request_context(request))
        except Exception:
            pass
        raise exc

    return handler
