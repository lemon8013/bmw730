"""app.system.search — data access.

Real SQL ``ILIKE`` queries across published/active entities. No external search
engine is involved.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.articles.model import BlogArticle
from app.platform.users.model import BizUser
from app.tools.catalog.model import Tool


class SearchRepository:
    """Data access for cross-entity search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_articles(self, term: str, *, limit: int) -> list[BlogArticle]:
        pattern = f"%{term}%"
        result = await self._session.execute(
            select(BlogArticle).where(
                BlogArticle.deleted_at.is_(None),
                BlogArticle.status == "PUBLISHED",
                (
                    BlogArticle.title.ilike(pattern)
                    | BlogArticle.summary.ilike(pattern)
                    | BlogArticle.content_markdown.ilike(pattern)
                ),
            )
            .order_by(BlogArticle.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_tools(self, term: str, *, limit: int) -> list[Tool]:
        pattern = f"%{term}%"
        result = await self._session.execute(
            select(Tool).where(
                Tool.deleted_at.is_(None),
                Tool.status == "PUBLISHED",
                (
                    Tool.name.ilike(pattern)
                    | Tool.code.ilike(pattern)
                    | Tool.summary.ilike(pattern)
                    | Tool.description.ilike(pattern)
                ),
            )
            .order_by(Tool.sort_order, Tool.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_users(self, term: str, *, limit: int) -> list[BizUser]:
        pattern = f"%{term}%"
        result = await self._session.execute(
            select(BizUser).where(
                BizUser.deleted_at.is_(None),
                BizUser.status == "ACTIVE",
                (BizUser.nickname.ilike(pattern) | BizUser.username.ilike(pattern)),
            )
            .order_by(BizUser.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
