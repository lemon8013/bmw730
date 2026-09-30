"""app.admin.users — data access."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysSession
from app.admin.departments.model import SysDepartment
from app.admin.roles.model import SysRole, SysUserRole
from app.admin.users.model import SysUser

ACTIVE_SESSION_STATUS: str = "ACTIVE"
ACTIVE_STATUS: str = "ACTIVE"


class AdminUserRepository:
    """Data access for administrator accounts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> SysUser | None:
        result = await self._session.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_including_deleted(self, user_id: int) -> SysUser | None:
        return await self._session.get(SysUser, user_id)

    async def search(
        self,
        *,
        keyword: str | None = None,
        department_id: int | None = None,
        status: str | None = None,
        department_ids: Sequence[int] | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysUser], int]:
        """Return one page of administrators and the total row count.

        ``department_ids`` is the data scope filter; ``None`` means "no filter".
        """
        conditions = [SysUser.deleted_at.is_(None)]
        if keyword:
            pattern = f"%{keyword.lower()}%"
            conditions.append(
                or_(
                    func.lower(SysUser.username).like(pattern),
                    func.lower(SysUser.display_name).like(pattern),
                    func.lower(func.coalesce(SysUser.email, "")).like(pattern),
                    func.lower(func.coalesce(SysUser.phone, "")).like(pattern),
                )
            )
        if department_id is not None:
            conditions.append(SysUser.department_id == department_id)
        if status:
            conditions.append(SysUser.status == status)
        if department_ids is not None:
            conditions.append(
                or_(SysUser.department_id.in_(department_ids), SysUser.department_id.is_(None))
            )

        total = int(
            (
                await self._session.execute(select(func.count(SysUser.id)).where(*conditions))
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(SysUser)
                    .where(*conditions)
                    .order_by(SysUser.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def exists_username(self, username: str, *, exclude_user_id: int | None = None) -> bool:
        conditions = [
            func.lower(SysUser.username) == username.lower(),
            SysUser.deleted_at.is_(None),
        ]
        if exclude_user_id is not None:
            conditions.append(SysUser.id != exclude_user_id)
        result = await self._session.execute(select(func.count(SysUser.id)).where(*conditions))
        return int(result.scalar_one()) > 0

    def add(self, user: SysUser) -> None:
        self._session.add(user)

    async def roles_of(self, user_id: int) -> list[SysRole]:
        result = await self._session.execute(
            select(SysRole)
            .join(SysUserRole, SysUserRole.role_id == SysRole.id)
            .where(SysUserRole.user_id == user_id, SysRole.deleted_at.is_(None))
            .order_by(SysRole.id)
        )
        return list(result.scalars())

    async def role_ids_of(self, user_id: int) -> list[int]:
        result = await self._session.execute(
            select(SysUserRole.role_id).where(SysUserRole.user_id == user_id)
        )
        return [int(row) for row in result.scalars()]

    async def replace_roles(self, user_id: int, role_ids: Sequence[int]) -> None:
        from sqlalchemy import delete

        await self._session.execute(delete(SysUserRole).where(SysUserRole.user_id == user_id))
        for role_id in role_ids:
            self._session.add(SysUserRole(user_id=user_id, role_id=role_id))
        await self._session.flush()

    async def find_roles(self, role_ids: Sequence[int]) -> list[SysRole]:
        if not role_ids:
            return []
        result = await self._session.execute(
            select(SysRole).where(SysRole.id.in_(role_ids), SysRole.deleted_at.is_(None))
        )
        return list(result.scalars())

    async def active_sessions_of(self, user_id: int) -> list[SysSession]:
        result = await self._session.execute(
            select(SysSession).where(
                SysSession.user_id == user_id,
                SysSession.session_status == ACTIVE_SESSION_STATUS,
                SysSession.revoked_at.is_(None),
            )
        )
        return list(result.scalars())

    async def revoke_sessions(
        self, session_ids: Sequence[int], *, reason: str, revoked_at: datetime.datetime
    ) -> int:
        if not session_ids:
            return 0
        result = await self._session.execute(
            update(SysSession)
            .where(SysSession.id.in_(session_ids), SysSession.revoked_at.is_(None))
            .values(session_status="REVOKED", revoked_at=revoked_at, revoke_reason=reason)
        )
        return int(result.rowcount or 0)

    async def online_sessions(self, *, department_ids: Sequence[int] | None) -> list[tuple]:
        """Return ``(user, session)`` pairs for every active session."""
        conditions = [
            SysSession.session_status == ACTIVE_SESSION_STATUS,
            SysSession.revoked_at.is_(None),
            SysUser.deleted_at.is_(None),
        ]
        if department_ids is not None:
            conditions.append(
                or_(SysUser.department_id.in_(department_ids), SysUser.department_id.is_(None))
            )
        result = await self._session.execute(
            select(SysUser, SysSession)
            .join(SysSession, SysSession.user_id == SysUser.id)
            .where(*conditions)
            .order_by(SysSession.last_active_at.desc(), SysSession.id.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def department_name(self, department_id: int | None) -> str | None:
        if department_id is None:
            return None
        row = await self._session.get(SysDepartment, department_id)
        return None if row is None else str(row.department_name)

    async def department_exists(self, department_id: int) -> bool:
        result = await self._session.execute(
            select(func.count(SysDepartment.id)).where(
                SysDepartment.id == department_id, SysDepartment.deleted_at.is_(None)
            )
        )
        return int(result.scalar_one()) > 0
