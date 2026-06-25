"""g8scope FastAPI adapter — captures unhandled exceptions from FastAPI/Starlette.

A thin layer over the runtime ``g8scope`` Python SDK. Add the middleware and any
unhandled exception is shipped to the g8scope ingest API; the project is
resolved server-side from the ingest key.
"""

from .context import request_context
from .middleware import (
    G8ScopeMiddleware,
    add_g8scope,
    g8scope_exception_handler,
)

__version__ = "1.0.0"

__all__ = [
    "G8ScopeMiddleware",
    "add_g8scope",
    "g8scope_exception_handler",
    "request_context",
    "__version__",
]
