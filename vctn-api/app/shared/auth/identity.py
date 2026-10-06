"""Identity resolution for an access token.

An access token is only a claim: the session it names must still exist, still be
active and not be revoked. Resolution therefore always touches the database,
which is also what makes "force logout" and "session revoked" take effect on the
very next request.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.users.model import SysUser
from app.core.exceptions import AuthenticationError
from app.platform.users.model import BizUser
from app.shared.auth.context import (
    SUBJECT_TYPE_ADMIN,
    SUBJECT_TYPE_PLATFORM,
    Principal,
)
from app.shared.security.tokens import AccessTokenClaims

ACTIVE_SESSION_STATUS: str = "ACTIVE"
ACTIVE_USER_STATUS: str = "ACTIVE"


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def resolve_principal(
    session: AsyncSession,
    claims: AccessTokenClaims,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> Principal:
    """Load the caller named by an access token.

    Raises:
        AuthenticationError: when the account or the session is gone, disabled,
            revoked or expired.
    """
    if claims.subject_type == SUBJECT_TYPE_ADMIN:
        return await _resolve_admin(session, claims, ip=ip, user_agent=user_agent)
    return await _resolve_platform(session, claims, ip=ip, user_agent=user_agent)


async def _resolve_admin(
    session: AsyncSession,
    claims: AccessTokenClaims,
    *,
    ip: str | None,
    user_agent: str | None,
) -> Principal:
    from app.admin.auth.model import SysSession

    row = (
        await session.execute(
            select(SysUser, SysSession)
            .join(SysSession, SysSession.id == claims.session_id)
            .where(
                SysUser.id == claims.subject_id,
                SysUser.deleted_at.is_(None),
                SysSession.user_id == claims.subject_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise AuthenticationError("session is no longer valid")
    user, sys_session = row

    if user.status != ACTIVE_USER_STATUS:
        raise AuthenticationError("account is not active")
    return Principal(
        subject_id=int(user.id),
        subject_type=SUBJECT_TYPE_ADMIN,
        session_id=int(sys_session.id),
        username=str(user.username),
        display_name=str(user.display_name),
        department_id=user.department_id,
        is_super_admin=bool(user.is_super_admin),
        ip=ip,
        user_agent=user_agent,
        must_change_password=bool(user.must_change_password),
    )


async def _resolve_platform(
    session: AsyncSession,
    claims: AccessTokenClaims,
    *,
    ip: str | None,
    user_agent: str | None,
) -> Principal:
    # Deferred on purpose: importing the session model at module scope would
    # pull more of the ORM graph into every admin request. It lives beside
    # `BizUser` in `users.model`, not in `auth.model`.
    from app.platform.users.model import BizUserSession

    row = (
        await session.execute(
            select(BizUser, BizUserSession)
            .join(BizUserSession, BizUserSession.id == claims.session_id)
            .where(
                BizUser.id == claims.subject_id,
                BizUser.deleted_at.is_(None),
                BizUserSession.user_id == claims.subject_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise AuthenticationError("session is no longer valid")
    user, user_session = row

    if user.status != ACTIVE_USER_STATUS:
        raise AuthenticationError("account is not active")
    return Principal(
        subject_id=int(user.id),
        subject_type=SUBJECT_TYPE_PLATFORM,
        session_id=int(user_session.id),
        username=str(user.username or ""),
        display_name=str(user.nickname or user.username or ""),
        ip=ip,
        user_agent=user_agent,
    )


def session_is_usable(
    *, status: str, expires_at: datetime | None, revoked_at: datetime | None
) -> bool:
    """Return whether a session row still admits requests."""
    if status != ACTIVE_SESSION_STATUS or revoked_at is not None:
        return False
    if expires_at is not None and expires_at <= _now():
        return False
    return True
