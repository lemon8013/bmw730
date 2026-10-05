"""app.admin.permissions — data access."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.permissions.model import SysPermission, SysPermissionField
from app.shared.ids import new_id

ACTIVE_STATUS: str = "ACTIVE"


class PermissionRepository:
    """Data access for permission resources and their field policies."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, permission_id: int) -> SysPermission | None:
        result = await self._session.execute(
            select(SysPermission).where(
                SysPermission.id == permission_id, SysPermission.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SysPermission]:
        result = await self._session.execute(
            select(SysPermission)
            .where(SysPermission.deleted_at.is_(None))
            .order_by(SysPermission.sort_order, SysPermission.id)
        )
        return list(result.scalars())

    async def list_page(self, *, offset: int, limit: int) -> list[SysPermission]:
        """Return one page of permission resources, ordered deterministically.

        The database does the slicing: fetching every row and paginating in
        Python would make the endpoint's cost grow with the size of the table
        instead of with the size of the page.
        """
        result = await self._session.execute(
            select(SysPermission)
            .where(SysPermission.deleted_at.is_(None))
            .order_by(SysPermission.sort_order, SysPermission.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars())

    async def count_all(self) -> int:
        """Return how many permission resources exist."""
        result = await self._session.execute(
            select(func.count(SysPermission.id)).where(SysPermission.deleted_at.is_(None))
        )
        return int(result.scalar_one())

    async def fields_of_many(
        self, permission_ids: Sequence[int]
    ) -> dict[int, list[SysPermissionField]]:
        """Return the field policies of several resources in one round trip.

        Reading them one resource at a time is an N+1: a page of 100 resources
        would issue 100 extra queries.
        """
        if not permission_ids:
            return {}
        result = await self._session.execute(
            select(SysPermissionField)
            .where(SysPermissionField.permission_id.in_(list(permission_ids)))
            .order_by(SysPermissionField.permission_id, SysPermissionField.field_code)
        )
        grouped: dict[int, list[SysPermissionField]] = {}
        for row in result.scalars():
            grouped.setdefault(int(row.permission_id), []).append(row)
        return grouped

    async def exists_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        conditions = [
            func.lower(SysPermission.permission_code) == code.lower(),
            SysPermission.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(SysPermission.id != exclude_id)
        result = await self._session.execute(
            select(func.count(SysPermission.id)).where(*conditions)
        )
        return int(result.scalar_one()) > 0

    def add(self, permission: SysPermission) -> None:
        self._session.add(permission)

    async def fields_of(self, permission_id: int) -> list[SysPermissionField]:
        result = await self._session.execute(
            select(SysPermissionField)
            .where(SysPermissionField.permission_id == permission_id)
            .order_by(SysPermissionField.field_code)
        )
        return list(result.scalars())

    async def replace_fields(
        self,
        permission_id: int,
        entries: Sequence[tuple[str, str]],
    ) -> None:
        from sqlalchemy import delete

        await self._session.execute(
            delete(SysPermissionField).where(SysPermissionField.permission_id == permission_id)
        )
        for field_code, field_mode in entries:
            self._session.add(
                SysPermissionField(
                    id=new_id(),
                    permission_id=permission_id,
                    field_code=field_code,
                    field_mode=field_mode,
                )
            )
        await self._session.flush()

    async def has_children(self, permission_id: int) -> bool:
        result = await self._session.execute(
            select(func.count(SysPermission.id)).where(
                SysPermission.parent_id == permission_id, SysPermission.deleted_at.is_(None)
            )
        )
        return int(result.scalar_one()) > 0
