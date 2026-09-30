"""HTTP middleware.

Phase 0 provides the trace-context middleware only, which satisfies the
``HTTP Request -> Middleware -> Router -> Service -> Repository`` trace
requirement.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.shared.tracing.context import reset_trace_context, set_trace_context

TRACE_ID_HEADER = "X-Trace-ID"
REQUEST_ID_HEADER = "X-Request-ID"

_SAFE_HEADER_VALUE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _resolve_header_value(raw: str | None) -> str:
    """Accept a client supplied identifier only when it is well formed."""
    if raw is not None and _SAFE_HEADER_VALUE.match(raw):
        return raw
    return uuid.uuid4().hex


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Propagates or generates X-Trace-ID / X-Request-ID for every request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = _resolve_header_value(request.headers.get(TRACE_ID_HEADER))
        request_id = _resolve_header_value(request.headers.get(REQUEST_ID_HEADER))

        request.state.trace_id = trace_id
        request.state.request_id = request_id

        tokens = set_trace_context(trace_id, request_id)
        try:
            response = await call_next(request)
        finally:
            reset_trace_context(tokens)

        response.headers[TRACE_ID_HEADER] = trace_id
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
