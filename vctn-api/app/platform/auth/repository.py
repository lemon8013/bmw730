"""app.platform.auth — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.users.model import (
    BizUser,
    BizUserLoginIdentity,
    BizUserLoginLog,
    BizUserPasswordHistory,
    BizUserSession,
    BizUserVerification,
)
from app.shared.ids import new_id

ACTIVE_SESSION_STATUS: str = "ACTIVE"
ACTIVE_STATUS: str = "ACTIVE"


class PlatformAuthRepository:
    """Data access for business user authentication."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_identity(self, identity_type: str, value: str) -> BizUserLoginIdentity | None:
        result = await self._session.execute(
            select(BizUserLoginIdentity).where(
                BizUserLoginIdentity.identity_type == identity_type,
                BizUserLoginIdentity.identity_value == value,
            )
        )
        return result.scalar_one_or_none()

    async def find_user_by_username(self, username: str) -> BizUser | None:
        result = await self._session.execute(
            select(BizUser).where(
                func.lower(BizUser.username) == username.lower(), BizUser.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def find_user(self, user_id: int) -> BizUser | None:
        result = await self._session.execute(
            select(BizUser).where(BizUser.id == user_id, BizUser.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def identities_of(self, user_id: int) -> list[BizUserLoginIdentity]:
        result = await self._session.execute(
            select(BizUserLoginIdentity).where(BizUserLoginIdentity.user_id == user_id)
        )
        return list(result.scalars())

    async def add_identity(
        self, *, user_id: int, identity_type: str, identity_value: str, verified: bool
    ) -> BizUserLoginIdentity:
        row = BizUserLoginIdentity(
            id=new_id(),
            user_id=user_id,
            identity_type=identity_type,
            identity_value=identity_value,
            verified=verified,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    def add_user(self, user: BizUser) -> None:
        self._session.add(user)

    async def recent_password_hashes(self, user_id: int, limit: int) -> list[str]:
        result = await self._session.execute(
            select(BizUserPasswordHistory.password_hash)
            .where(BizUserPasswordHistory.user_id == user_id)
            .order_by(BizUserPasswordHistory.created_at.desc(), BizUserPasswordHistory.id.desc())
            .limit(limit)
        )
        return [str(row) for row in result.scalars()]

    async def add_password_history(self, *, user_id: int, password_hash: str) -> None:
        self._session.add(BizUserPasswordHistory(user_id=user_id, password_hash=password_hash))
        await self._session.flush()

    async def trim_password_history(self, user_id: int, keep: int) -> None:
        from sqlalchemy import delete

        identifiers = (
            (
                await self._session.execute(
                    select(BizUserPasswordHistory.id)
                    .where(BizUserPasswordHistory.user_id == user_id)
                    .order_by(
                        BizUserPasswordHistory.created_at.desc(), BizUserPasswordHistory.id.desc()
                    )
                )
            )
            .scalars()
            .all()
        )
        stale = [int(row) for row in identifiers[keep:]]
        if stale:
            await self._session.execute(
                delete(BizUserPasswordHistory).where(BizUserPasswordHistory.id.in_(stale))
            )

    async def list_active_sessions(self, user_id: int) -> list[BizUserSession]:
        result = await self._session.execute(
            select(BizUserSession)
            .where(
                BizUserSession.user_id == user_id,
                BizUserSession.session_status == ACTIVE_SESSION_STATUS,
                BizUserSession.revoked_at.is_(None),
            )
            .order_by(BizUserSession.login_at, BizUserSession.id)
        )
        return list(result.scalars())

    async def oldest_active_session_ids(self, user_id: int, keep: int) -> list[int]:
        active = await self.list_active_sessions(user_id)
        if len(active) <= keep:
            return []
        return [int(row.id) for row in active[: len(active) - keep]]

    async def create_session(
        self,
        *,
        user_id: int,
        refresh_token_hash: str,
        anonymous_id_hash: str | None,
        ip: str | None,
        user_agent: str | None,
        device_type: str | None,
        login_at: datetime.datetime,
        expires_at: datetime.datetime,
    ) -> BizUserSession:
        row = BizUserSession(
            id=new_id(),
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            session_status=ACTIVE_SESSION_STATUS,
            anonymous_id_hash=anonymous_id_hash,
            ip=ip,
            user_agent=user_agent,
            device_type=device_type,
            login_at=login_at,
            last_active_at=login_at,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_session_by_refresh_hash(self, digest: str) -> BizUserSession | None:
        result = await self._session.execute(
            select(BizUserSession).where(BizUserSession.refresh_token_hash == digest)
        )
        return result.scalar_one_or_none()

    async def revoke_sessions(
        self, session_ids: list[int], *, reason: str, revoked_at: datetime.datetime
    ) -> int:
        if not session_ids:
            return 0
        result = await self._session.execute(
            update(BizUserSession)
            .where(BizUserSession.id.in_(session_ids), BizUserSession.revoked_at.is_(None))
            .values(session_status="REVOKED", revoked_at=revoked_at, revoke_reason=reason)
        )
        return int(result.rowcount or 0)

    async def count_recent_failures(self, user_id: int, *, since: datetime.datetime) -> int:
        """Return how many failed logins happened since ``since``.

        ``biz_user`` has no failure counter column, so the brute force state is
        derived from the login log instead of being invented as a new field.
        """
        result = await self._session.execute(
            select(func.count(BizUserLoginLog.id)).where(
                BizUserLoginLog.user_id == user_id,
                BizUserLoginLog.success.is_(False),
                BizUserLoginLog.occurred_at >= since,
            )
        )
        return int(result.scalar_one())

    async def add_login_log(self, **fields: object) -> None:
        self._session.add(BizUserLoginLog(**fields))  # type: ignore[arg-type]
        await self._session.flush()

    async def add_verification(self, **fields: object) -> BizUserVerification:
        row = BizUserVerification(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_verification(self, verification_id: int) -> BizUserVerification | None:
        return await self._session.get(BizUserVerification, verification_id)

    async def mark_identity_verified(self, *, user_id: int, identity_type: str) -> None:
        await self._session.execute(
            update(BizUserLoginIdentity)
            .where(
                BizUserLoginIdentity.user_id == user_id,
                BizUserLoginIdentity.identity_type == identity_type,
            )
            .values(verified=True)
        )
