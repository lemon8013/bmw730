"""app.admin.dictionaries — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dictionaries.model import SysDictItem, SysDictType


class DictionaryRepository:
    """Data access for dictionary types and items."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_type(self, type_id: int) -> SysDictType | None:
        result = await self._session.execute(
            select(SysDictType).where(SysDictType.id == type_id, SysDictType.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_types(self) -> list[SysDictType]:
        result = await self._session.execute(
            select(SysDictType).where(SysDictType.deleted_at.is_(None)).order_by(SysDictType.id)
        )
        return list(result.scalars())

    async def item_counts(self) -> dict[int, int]:
        result = await self._session.execute(
            select(SysDictItem.dict_type_id, func.count(SysDictItem.id))
            .where(SysDictItem.deleted_at.is_(None))
            .group_by(SysDictItem.dict_type_id)
        )
        return {int(row[0]): int(row[1]) for row in result.all()}

    async def exists_type_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        conditions = [
            func.lower(SysDictType.dict_code) == code.lower(),
            SysDictType.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(SysDictType.id != exclude_id)
        result = await self._session.execute(select(func.count(SysDictType.id)).where(*conditions))
        return int(result.scalar_one()) > 0

    def add_type(self, row: SysDictType) -> None:
        self._session.add(row)

    async def soft_delete_type(self, type_id: int, *, now: datetime.datetime) -> None:
        await self._session.execute(
            update(SysDictType)
            .where(SysDictType.id == type_id)
            .values(deleted_at=now, status="DISABLED")
        )
        await self._session.execute(
            update(SysDictItem).where(SysDictItem.dict_type_id == type_id).values(deleted_at=now)
        )
        await self._session.flush()

    async def get_item(self, item_id: int) -> SysDictItem | None:
        result = await self._session.execute(
            select(SysDictItem).where(SysDictItem.id == item_id, SysDictItem.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_items(self, type_id: int) -> list[SysDictItem]:
        result = await self._session.execute(
            select(SysDictItem)
            .where(SysDictItem.dict_type_id == type_id, SysDictItem.deleted_at.is_(None))
            .order_by(SysDictItem.sort_order, SysDictItem.id)
        )
        return list(result.scalars())

    async def exists_item_value(
        self, type_id: int, value: str, *, exclude_id: int | None = None
    ) -> bool:
        conditions = [
            SysDictItem.dict_type_id == type_id,
            SysDictItem.item_value == value,
            SysDictItem.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(SysDictItem.id != exclude_id)
        result = await self._session.execute(select(func.count(SysDictItem.id)).where(*conditions))
        return int(result.scalar_one()) > 0

    def add_item(self, row: SysDictItem) -> None:
        self._session.add(row)

    async def clear_default_flag(self, type_id: int, *, exclude_id: int | None = None) -> None:
        conditions = [SysDictItem.dict_type_id == type_id, SysDictItem.is_default.is_(True)]
        if exclude_id is not None:
            conditions.append(SysDictItem.id != exclude_id)
        await self._session.execute(update(SysDictItem).where(*conditions).values(is_default=False))

    async def soft_delete_item(self, item_id: int, *, now: datetime.datetime) -> None:
        await self._session.execute(
            update(SysDictItem)
            .where(SysDictItem.id == item_id)
            .values(deleted_at=now, status="DISABLED")
        )
        await self._session.flush()
