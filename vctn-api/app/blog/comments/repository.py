"""app.blog.comments — data access.

Public readers only ever see ``APPROVED`` comments; the repository exposes a
dedicated query for that and a separate pending queue for the admin reviewer.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.comments.model import BlogComment


class CommentRepository:
    """Data access for blog comments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_approved(
        self, article_id: int, *, limit: int, offset: int
    ) -> tuple[list[BlogComment], int]:
        base = select(BlogComment).where(
            BlogComment.deleted_at.is_(None),
            BlogComment.article_id == article_id,
            BlogComment.status == "APPROVED",
        )
        total = int(
            (
                await self._session.execute(
                    select(func.count(BlogComment.id)).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(BlogComment.created_at.asc(), BlogComment.id.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_pending(self, *, limit: int, offset: int) -> tuple[list[BlogComment], int]:
        base = select(BlogComment).where(
            BlogComment.deleted_at.is_(None),
            BlogComment.status == "PENDING",
        )
        total = int(
            (
                await self._session.execute(
                    select(func.count(BlogComment.id)).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(BlogComment.created_at.asc(), BlogComment.id.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_any(self, comment_id: int) -> BlogComment | None:
        row = await self._session.get(BlogComment, comment_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def create(self, **fields: object) -> BlogComment:
        row = BlogComment(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_status(
        self, row: BlogComment, *, status: str, reviewer_id: int | None
    ) -> None:
        row.status = status
        row.reviewer_id = reviewer_id
        row.reviewed_at = datetime.datetime.now(datetime.UTC)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def soft_delete(self, row: BlogComment) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
