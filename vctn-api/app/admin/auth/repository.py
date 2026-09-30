"""app.admin.auth — data access.

The repository only reads and writes rows; it never commits and never decides a
business rule. The transaction belongs to
:mod:`app.admin.auth.service`.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysPasswordHistory, SysSession
from app.admin.users.model import SysUser

ACTIVE_SESSION_STATUS: str = "ACTIVE"


class AdminAuthRepository:
    """Data access for administrator authentication."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user_by_username(self, username: str) -> SysUser | None:
        result = await self._session.execute(
            select(SysUser).where(
                func.lower(SysUser.username) == username.lower(),
                SysUser.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_user_by_id(self, user_id: int) -> SysUser | None:
        result = await self._session.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def count_active_sessions(self, user_id: int) -> int:
        result = await self._session.execute(
            select(func.count(SysSession.id)).where(
                SysSession.user_id == user_id,
                SysSession.session_status == ACTIVE_SESSION_STATUS,
                SysSession.revoked_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def list_active_sessions(self, user_id: int) -> Sequence[SysSession]:
        result = await self._session.execute(
            select(SysSession)
            .where(
                SysSession.user_id == user_id,
                SysSession.session_status == ACTIVE_SESSION_STATUS,
                SysSession.revoked_at.is_(None),
            )
            .order_by(SysSession.login_at, SysSession.id)
        )
        return result.scalars().all()

    async def oldest_active_session_ids(self, user_id: int, keep: int) -> list[int]:
        """Return the ids of the oldest sessions beyond the ``keep`` newest."""
        active = await self.list_active_sessions(user_id)
        if len(active) <= keep:
            return []
        return [int(row.id) for row in active[: len(active) - keep]]

    async def create_session(
        self,
        *,
        user_id: int,
        refresh_token_hash: str,
        ip: str | None,
        user_agent: str | None,
        device_type: str | None,
        login_at: datetime.datetime,
        expires_at: datetime.datetime,
    ) -> SysSession:
        session = SysSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            session_status=ACTIVE_SESSION_STATUS,
            ip=ip,
            user_agent=user_agent,
            device_type=device_type,
            login_at=login_at,
            last_active_at=login_at,
            expires_at=expires_at,
        )
        self._session.add(session)
        await self._session.flush()
        return session

    async def find_session_by_refresh_hash(self, refresh_token_hash: str) -> SysSession | None:
        result = await self._session.execute(
            select(SysSession).where(SysSession.refresh_token_hash == refresh_token_hash)
        )
        return result.scalar_one_or_none()

    async def find_session(self, session_id: int) -> SysSession | None:
        return await self._session.get(SysSession, session_id)

    async def revoke_sessions(
        self,
        session_ids: Sequence[int],
        *,
        reason: str,
        revoked_at: datetime.datetime,
    ) -> int:
        if not session_ids:
            return 0
        result = await self._session.execute(
            update(SysSession)
            .where(SysSession.id.in_(session_ids), SysSession.revoked_at.is_(None))
            .values(
                session_status="REVOKED",
                revoked_at=revoked_at,
                revoke_reason=reason,
            )
        )
        return int(result.rowcount or 0)

    async def touch_session(self, session: SysSession, *, now: datetime.datetime) -> None:
        session.last_active_at = now
        await self._session.flush()

    async def recent_password_hashes(self, user_id: int, limit: int) -> list[str]:
        result = await self._session.execute(
            select(SysPasswordHistory.password_hash)
            .where(SysPasswordHistory.user_id == user_id)
            .order_by(SysPasswordHistory.created_at.desc(), SysPasswordHistory.id.desc())
            .limit(limit)
        )
        return [str(row) for row in result.scalars()]

    async def add_password_history(self, *, user_id: int, password_hash: str) -> None:
        self._session.add(SysPasswordHistory(user_id=user_id, password_hash=password_hash))
        await self._session.flush()

    async def trim_password_history(self, user_id: int, keep: int) -> None:
        """Keep only the newest ``keep`` history rows for a user."""
        identifiers = (
            (
                await self._session.execute(
                    select(SysPasswordHistory.id)
                    .where(SysPasswordHistory.user_id == user_id)
                    .order_by(SysPasswordHistory.created_at.desc(), SysPasswordHistory.id.desc())
                )
            )
            .scalars()
            .all()
        )
        stale = [int(row) for row in identifiers[keep:]]
        if not stale:
            return
        from sqlalchemy import delete

        await self._session.execute(
            delete(SysPasswordHistory).where(SysPasswordHistory.id.in_(stale))
        )
