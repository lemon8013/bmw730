"""Trace ID / Request ID context.

The middleware writes the identifiers here so that Router, Service and
Repository code can read them without threading a parameter through every call.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

TraceToken = tuple[Token[str | None], Token[str | None]]

_TRACE_ID: ContextVar[str | None] = ContextVar("vctn_trace_id", default=None)
_REQUEST_ID: ContextVar[str | None] = ContextVar("vctn_request_id", default=None)


def set_trace_context(trace_id: str, request_id: str) -> TraceToken:
    """Bind trace_id / request_id to the current execution context."""
    return _TRACE_ID.set(trace_id), _REQUEST_ID.set(request_id)


def reset_trace_context(tokens: TraceToken) -> None:
    """Restore the previous trace context."""
    trace_token, request_token = tokens
    _TRACE_ID.reset(trace_token)
    _REQUEST_ID.reset(request_token)


def get_trace_id() -> str | None:
    """Return the trace id of the current request, if any."""
    return _TRACE_ID.get()


def get_request_id() -> str | None:
    """Return the request id of the current request, if any."""
    return _REQUEST_ID.get()
