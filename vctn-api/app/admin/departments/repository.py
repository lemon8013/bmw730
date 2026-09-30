"""app.admin.departments — data access."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.departments.model import SysDepartment
from app.admin.users.model import SysUser


class DepartmentRepository:
    """Data access for departments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, department_id: int) -> SysDepartment | None:
        result = await self._session.execute(
            select(SysDepartment).where(
                SysDepartment.id == department_id, SysDepartment.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SysDepartment]:
        result = await self._session.execute(
            select(SysDepartment)
            .where(SysDepartment.deleted_at.is_(None))
            .order_by(SysDepartment.sort_order, SysDepartment.id)
        )
        return list(result.scalars())

    async def list_visible(self, department_ids: Sequence[int] | None) -> list[SysDepartment]:
        """Return every department, or only the ones inside a data scope."""
        conditions = [SysDepartment.deleted_at.is_(None)]
        if department_ids is not None:
            conditions.append(SysDepartment.id.in_(list(department_ids)))
        result = await self._session.execute(
            select(SysDepartment)
            .where(*conditions)
            .order_by(SysDepartment.sort_order, SysDepartment.id)
        )
        return list(result.scalars())

    async def children(self, parent_id: int) -> list[SysDepartment]:
        result = await self._session.execute(
            select(SysDepartment)
            .where(SysDepartment.parent_id == parent_id, SysDepartment.deleted_at.is_(None))
            .order_by(SysDepartment.sort_order, SysDepartment.id)
        )
        return list(result.scalars())

    async def descendant_ids(self, department_id: int) -> set[int]:
        """Return the department and every descendant below it."""
        rows = await self.list_all()
        children_of: dict[int | None, list[int]] = {}
        for row in rows:
            children_of.setdefault(row.parent_id, []).append(int(row.id))
        collected: set[int] = set()
        stack = [department_id]
        while stack:
            current = stack.pop()
            if current in collected:
                continue
            collected.add(current)
            stack.extend(children_of.get(current, []))
        return collected

    async def exists_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        conditions = [
            func.lower(SysDepartment.department_code) == code.lower(),
            SysDepartment.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(SysDepartment.id != exclude_id)
        result = await self._session.execute(
            select(func.count(SysDepartment.id)).where(*conditions)
        )
        return int(result.scalar_one()) > 0

    async def count_users(self, department_id: int) -> int:
        result = await self._session.execute(
            select(func.count(SysUser.id)).where(
                SysUser.department_id == department_id, SysUser.deleted_at.is_(None)
            )
        )
        return int(result.scalar_one())

    async def user_counts(self) -> dict[int, int]:
        result = await self._session.execute(
            select(SysUser.department_id, func.count(SysUser.id))
            .where(SysUser.deleted_at.is_(None), SysUser.department_id.is_not(None))
            .group_by(SysUser.department_id)
        )
        return {int(row[0]): int(row[1]) for row in result.all()}

    async def users_of(self, department_id: int) -> list[SysUser]:
        result = await self._session.execute(
            select(SysUser)
            .where(SysUser.department_id == department_id, SysUser.deleted_at.is_(None))
            .order_by(SysUser.id)
        )
        return list(result.scalars())

    def add(self, department: SysDepartment) -> None:
        self._session.add(department)

    async def soft_delete(self, department: SysDepartment, *, now: datetime.datetime) -> None:
        department.deleted_at = now
        department.status = "DISABLED"
        await self._session.flush()
