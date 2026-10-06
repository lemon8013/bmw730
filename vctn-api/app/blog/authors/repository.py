"""app.blog.authors — data access.

Blog authors and their applications. Neither table has a soft-delete column, so
existence checks rely on the primary key / unique constraint instead.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.authors.model import BlogAuthor, BlogAuthorApplication


class AuthorRepository:
    """Data access for blog authors and author applications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_authors(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> tuple[list[BlogAuthor], int]:
        base = select(BlogAuthor)
        if status:
            base = base.where(BlogAuthor.status == status)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(BlogAuthor.created_at.desc(), BlogAuthor.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, author_id: int) -> BlogAuthor | None:
        return await self._session.get(BlogAuthor, author_id)

    async def get_by_user_id(self, user_id: int) -> BlogAuthor | None:
        result = await self._session.execute(
            select(BlogAuthor).where(BlogAuthor.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_author(self, **fields: object) -> BlogAuthor:
        row = BlogAuthor(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_author(self, row: BlogAuthor, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def list_applications(
        self, *, status: str | None = None, limit: int, offset: int
    ) -> tuple[list[BlogAuthorApplication], int]:
        base = select(BlogAuthorApplication)
        if status:
            base = base.where(BlogAuthorApplication.status == status)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(
                        BlogAuthorApplication.applied_at.desc(),
                        BlogAuthorApplication.id.desc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_application(self, application_id: int) -> BlogAuthorApplication | None:
        return await self._session.get(BlogAuthorApplication, application_id)

    async def get_application_by_user(
        self, user_id: int
    ) -> BlogAuthorApplication | None:
        result = await self._session.execute(
            select(BlogAuthorApplication)
            .where(BlogAuthorApplication.user_id == user_id)
            .order_by(BlogAuthorApplication.applied_at.desc())
        )
        return result.scalars().first()

    async def create_application(self, **fields: object) -> BlogAuthorApplication:
        row = BlogAuthorApplication(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_application(
        self, row: BlogAuthorApplication, **fields: object
    ) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()
