"""FastAPI dependencies for authentication and authorization.

A controller receives an already authorized :class:`Principal`; it never
evaluates a role or a permission itself.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import DbSessionDep
from app.core.exceptions import AuthenticationError
from app.shared.auth.context import (
    SUBJECT_TYPE_ADMIN,
    SUBJECT_TYPE_PLATFORM,
    Principal,
)
from app.shared.auth.identity import resolve_principal
from app.shared.authorization.service import AuthorizationService
from app.shared.logging.writers import RESULT_FAILURE, write_security_log
from app.shared.security.masking import mask_token
from app.shared.security.tokens import decode_access_token

_BEARER = HTTPBearer(auto_error=False, description="Bearer <access-token>")


async def _record_auth_failure(
    request: Request,
    *,
    event_type: str,
    error_code: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Persist an authentication failure in its own short transaction."""
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_factory", None
    )
    if factory is None:
        return
    async with factory() as session:
        await write_security_log(
            session,
            event_type=event_type,
            result=RESULT_FAILURE,
            error_code=error_code,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata=metadata,
        )
        await session.commit()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def resolve_optional_principal(
    request: Request,
    session: DbSessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_BEARER)],
) -> Principal | None:
    """Return the caller of the request, or ``None`` for an anonymous request."""
    if credentials is None:
        return None
    try:
        claims = decode_access_token(credentials.credentials)
    except AuthenticationError as exc:
        await _record_auth_failure(
            request,
            event_type="TOKEN_INVALID",
            error_code=str(exc.code),
            metadata={"token": mask_token(credentials.credentials)},
        )
        raise
    try:
        return await resolve_principal(
            session,
            claims,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthenticationError as exc:
        await _record_auth_failure(
            request,
            event_type="SESSION_INVALID",
            error_code=str(exc.code),
            metadata={"subject_id": claims.subject_id},
        )
        raise


async def resolve_current_principal(
    principal: Annotated[Principal | None, Depends(resolve_optional_principal)],
) -> Principal:
    """Return the authenticated caller or fail with ``401``."""
    if principal is None:
        raise AuthenticationError("authentication required")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(resolve_current_principal)]
OptionalPrincipal = Annotated[Principal | None, Depends(resolve_optional_principal)]


async def require_admin(principal: CurrentPrincipal) -> Principal:
    """Fail when the caller is not an administrator."""
    if principal.subject_type != SUBJECT_TYPE_ADMIN:
        raise AuthenticationError("an administrator identity is required")
    return principal


async def require_platform_user(principal: CurrentPrincipal) -> Principal:
    """Fail when the caller is not a business user."""
    if principal.subject_type != SUBJECT_TYPE_PLATFORM:
        raise AuthenticationError("a business user identity is required")
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
PlatformPrincipal = Annotated[Principal, Depends(require_platform_user)]


def require_permission(permission_code: str):
    """Build a dependency that enforces one admin permission.

    The route declares the permission it needs next to its path, and receives an
    already authorized :class:`Principal`::

        principal: Principal = Depends(require_permission("USER_VIEW"))
    """

    async def _dependency(
        principal: AdminPrincipal,
        session: DbSessionDep,
    ) -> Principal:
        service = AuthorizationService()
        await service.require_permission(session, principal, permission_code)
        return principal

    _dependency.__name__ = f"require_permission_{permission_code.lower()}"
    return _dependency


def require_any_permission(*permission_codes: str):
    """Build a dependency that enforces at least one of the given permissions."""

    async def _dependency(principal: AdminPrincipal, session: DbSessionDep) -> Principal:
        service = AuthorizationService()
        for code in permission_codes:
            if await service.has_permission(session, principal, code):
                return principal
        await service.require_permission(session, principal, permission_codes[0])
        return principal

    _dependency.__name__ = "require_any_permission"
    return _dependency
