"""Build envelope context from a Starlette/FastAPI request.

Tolerant and duck-typed: anything that quacks like a Starlette ``Request``
(``method``, ``url``, ``headers``) works, so unit tests need not stand up a
real ASGI app. Sensitive headers (``authorization``, ``cookie``) are dropped
before they ever reach the SDK — PII scrub is the SDK's job for everything
else, but we never even forward credentials.
"""

from __future__ import annotations

from typing import Any, Dict

# Headers we never forward, regardless of server-side scrubbing.
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}


def request_context(request: Any) -> Dict[str, Any]:
    """Return an envelope ``context`` dict for a request.

    Never raises: a malformed request degrades to ``{"custom": {}}`` rather
    than breaking capture (which would, in turn, break the host app).
    """
    try:
        return {
            "request": {
                "method": _method(request),
                "url": _url(request),
                "headers": _headers(request),
            },
            "custom": {},
        }
    except Exception:
        return {"custom": {}}


def _method(request: Any) -> str:
    return str(getattr(request, "method", "") or "")


def _url(request: Any) -> str:
    url = getattr(request, "url", None)
    if url is None:
        return ""
    return str(url)


def _headers(request: Any) -> Dict[str, str]:
    raw = getattr(request, "headers", None)
    if raw is None:
        return {}
    try:
        items = raw.items()
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for name, value in items:
        if str(name).lower() in _SENSITIVE_HEADERS:
            continue
        out[str(name)] = str(value)
    return out
