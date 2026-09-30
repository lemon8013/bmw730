"""HTTP middleware.

Phase 0 provides the trace-context middleware only, which satisfies the
``HTTP Request -> Middleware -> Router -> Service -> Repository`` trace
requirement.

Header names and the accepted identifier length are configuration, read from
:class:`app.core.config.Settings` via ``request.app.state.settings``.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable
from functools import lru_cache

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import Settings
from app.shared.tracing.context import reset_trace_context, set_trace_context

TRACE_ID_HEADER = "X-Trace-ID"
REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_MAX_LENGTH = 128

_SAFE_CHARACTERS = r"A-Za-z0-9._:\-"


@lru_cache(maxsize=8)
def _safe_header_value_pattern(max_length: int) -> re.Pattern[str]:
    """Compile the accepted identifier pattern for the configured length."""
    return re.compile(rf"^[{_SAFE_CHARACTERS}]{{1,{max_length}}}$")


def _resolve_header_value(
    raw: str | None,
    pattern: re.Pattern[str],
) -> str:
    """Accept a client supplied identifier only when it is well formed."""
    if raw is not None and pattern.match(raw):
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
        settings: Settings | None = getattr(request.app.state, "settings", None)
        trace_header = settings.TRACE_ID_HEADER if settings else TRACE_ID_HEADER
        request_header = settings.REQUEST_ID_HEADER if settings else REQUEST_ID_HEADER
        max_length = settings.TRACE_ID_MAX_LENGTH if settings else TRACE_ID_MAX_LENGTH
        pattern = _safe_header_value_pattern(max_length)

        trace_id = _resolve_header_value(request.headers.get(trace_header), pattern)
        request_id = _resolve_header_value(request.headers.get(request_header), pattern)

        request.state.trace_id = trace_id
        request.state.request_id = request_id

        tokens = set_trace_context(trace_id, request_id)
        try:
            response = await call_next(request)
        finally:
            reset_trace_context(tokens)

        response.headers[trace_header] = trace_id
        response.headers[request_header] = request_id
        return response
