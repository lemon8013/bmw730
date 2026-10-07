"""Browser facing security headers and Host allow-listing.

Both middlewares read their policy from :class:`app.core.config.Settings` via
``request.app.state.settings`` so that nothing here is hard coded.

Two deliberate design choices:

* **HSTS is opt in.** Sending ``Strict-Transport-Security`` while TLS is not
  terminated in front of the application makes a browser refuse the plain HTTP
  origin for the whole max-age, which looks exactly like an outage. It is
  switched on by configuration once HTTPS is live.
* **A blank policy means "omit the header", never "send a permissive one".**
  An unset CSP must not silently turn into ``default-src *``; that would look
  configured while protecting nothing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import Settings

CONTENT_TYPE_OPTIONS: Final[str] = "nosniff"
#: Paths the load balancer and the container runtime poll. They carry no
#: business data, so a Host mismatch must not turn into false alarms.
HOST_CHECK_EXEMPT_PATHS: Final[frozenset[str]] = frozenset(
    {"/health", "/ready", "/version"}
)


def _hsts_value(settings: Settings) -> str:
    """Render the HSTS header value for the configured policy."""
    value = f"max-age={settings.SECURITY_HSTS_MAX_AGE_SECONDS}"
    if settings.SECURITY_HSTS_INCLUDE_SUBDOMAINS:
        value = f"{value}; includeSubDomains"
    return value


def _apply_security_headers(response: Response, settings: Settings) -> None:
    """Attach every configured security header to ``response``."""
    # Always on: there is no configuration in which sniffing or framing
    # should be allowed, unless the operator blanks the framing policy.
    response.headers["X-Content-Type-Options"] = CONTENT_TYPE_OPTIONS

    if settings.SECURITY_HSTS_ENABLED:
        response.headers["Strict-Transport-Security"] = _hsts_value(settings)

    frame_options = settings.SECURITY_FRAME_OPTIONS.strip()
    if frame_options:
        response.headers["X-Frame-Options"] = frame_options

    referrer_policy = settings.SECURITY_REFERRER_POLICY.strip()
    if referrer_policy:
        response.headers["Referrer-Policy"] = referrer_policy

    permissions_policy = settings.SECURITY_PERMISSIONS_POLICY.strip()
    if permissions_policy:
        response.headers["Permissions-Policy"] = permissions_policy

    csp = settings.SECURITY_CSP.strip()
    if csp:
        header = (
            "Content-Security-Policy-Report-Only"
            if settings.SECURITY_CSP_REPORT_ONLY
            else "Content-Security-Policy"
        )
        response.headers[header] = csp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds the browser security headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        settings: Settings | None = getattr(request.app.state, "settings", None)
        if settings is not None:
            _apply_security_headers(response, settings)
        return response


class AllowedHostsMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Host header is not on the allow-list.

    Without this, an attacker can supply an arbitrary Host and poison any
    absolute URL the application builds - password reset links above all. The
    check is skipped for the system probes so that a plain container health
    check does not depend on the header being correct.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings: Settings | None = getattr(request.app.state, "settings", None)
        if settings is None:
            return await call_next(request)

        allowed = settings.allowed_hosts
        if not allowed or request.url.path in HOST_CHECK_EXEMPT_PATHS:
            return await call_next(request)

        host = (request.headers.get("host") or "").strip().lower()
        # The header may carry a port; the allow-list is host names only.
        hostname = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
        if hostname in allowed:
            return await call_next(request)

        return JSONResponse(
            status_code=400,
            content={
                "code": 400000,
                "message": "invalid host header",
                "data": None,
            },
        )
