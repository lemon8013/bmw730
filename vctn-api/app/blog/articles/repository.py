"""app.blog.articles — data access.

The repository only reads and writes rows. The service decides visibility
(public list shows only published, non deleted rows) and owns the transaction.
"""

from __future__ import annotations

import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.articles.model import BlogArticle, BlogArticleTag
from app.shared.ids import new_id


class ArticleRepository:
    """Data access for blog articles and their tags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_published(
        self,
        *,
        keyword: str | None = None,
        category_id: int | None = None,
        author_id: int | None = None,
        status: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BlogArticle], int]:
        base = select(BlogArticle).where(
            BlogArticle.deleted_at.is_(None),
            BlogArticle.status == (status or "PUBLISHED"),
        )
        if keyword:
            base = base.where(
                BlogArticle.title.ilike(f"%{keyword}%")
                | BlogArticle.summary.ilike(f"%{keyword}%")
            )
        if category_id is not None:
            base = base.where(BlogArticle.category_id == category_id)
        if author_id is not None:
            base = base.where(BlogArticle.author_id == author_id)
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
                    base.order_by(BlogArticle.published_at.desc(), BlogArticle.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_pending(
        self, *, limit: int, offset: int
    ) -> tuple[list[BlogArticle], int]:
        base = select(BlogArticle).where(
            BlogArticle.deleted_at.is_(None),
            BlogArticle.review_status.in_(["PENDING"]),
        )
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
                    base.order_by(BlogArticle.updated_at.desc(), BlogArticle.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_published(self, article_id: int) -> BlogArticle | None:
        row = await self._session.get(BlogArticle, article_id)
        if row is None or row.deleted_at is not None or row.status != "PUBLISHED":
            return None
        return row

    async def get_any(self, article_id: int) -> BlogArticle | None:
        row = await self._session.get(BlogArticle, article_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_slug(self, slug: str) -> BlogArticle | None:
        result = await self._session.execute(
            select(BlogArticle).where(
                BlogArticle.slug == slug, BlogArticle.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> BlogArticle:
        row = BlogArticle(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: BlogArticle, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: BlogArticle) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def increment_view(self, row: BlogArticle) -> None:
        row.view_count = int(row.view_count or 0) + 1
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def adjust_count(self, article_id: int, field: str, delta: int) -> None:
        row = await self._session.get(BlogArticle, article_id)
        if row is None:
            return
        current = int(getattr(row, field) or 0) + delta
        setattr(row, field, max(current, 0))
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_tags(self, article_id: int) -> list[str]:
        result = await self._session.execute(
            select(BlogArticleTag.tag_name).where(
                BlogArticleTag.article_id == article_id
            )
        )
        return [str(name) for name in result.scalars().all()]

    async def set_tags(self, article_id: int, tag_names: list[str]) -> None:
        await self._session.execute(
            delete(BlogArticleTag).where(BlogArticleTag.article_id == article_id)
        )
        seen: set[str] = set()
        for name in tag_names:
            normalized = name.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            self._session.add(
                BlogArticleTag(id=new_id(), article_id=article_id, tag_name=normalized)
            )
        await self._session.flush()
