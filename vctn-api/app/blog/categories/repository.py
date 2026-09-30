"""app.blog.categories — data access.

Repository methods never commit and never decide business rules: they only
read and write rows, the service layer owns the transaction and the policy.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.categories.model import BlogCategory


class CategoryRepository:
    """Data access for blog categories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BlogCategory], int]:
        base = select(BlogCategory).where(BlogCategory.deleted_at.is_(None))
        if keyword:
            base = base.where(BlogCategory.category_name.ilike(f"%{keyword}%"))
        if status:
            base = base.where(BlogCategory.status == status)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BlogCategory.id)).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(
                        BlogCategory.sort_order.asc(), BlogCategory.id.asc()
                    ).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, category_id: int) -> BlogCategory | None:
        row = await self._session.get(BlogCategory, category_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_code(self, category_code: str) -> BlogCategory | None:
        result = await self._session.execute(
            select(BlogCategory).where(
                BlogCategory.category_code == category_code,
                BlogCategory.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> BlogCategory:
        row = BlogCategory(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: BlogCategory, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: BlogCategory) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
