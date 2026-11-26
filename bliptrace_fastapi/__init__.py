"""Bliptrace FastAPI adapter — captures unhandled exceptions from FastAPI/Starlette.

A thin layer over the runtime ``bliptrace`` Python SDK. Add the middleware and any
unhandled exception is shipped to the Bliptrace ingest API; the project is
resolved server-side from the ingest key.
"""

from .context import request_context
from .middleware import (
    BliptraceMiddleware,
    add_bliptrace,
    bliptrace_exception_handler,
)

__version__ = "1.0.0"

__all__ = [
    "BliptraceMiddleware",
    "add_bliptrace",
    "bliptrace_exception_handler",
    "request_context",
    "__version__",
]
