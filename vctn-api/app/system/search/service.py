"""app.system.search — business logic.

Aggregates matches across articles, tools and users into a single result list.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.system.search.repository import SearchRepository
from app.system.search.schema import SearchResultItem

_TYPE_ALL = "all"
_TYPE_ARTICLE = "article"
_TYPE_TOOL = "tool"
_TYPE_USER = "user"

_PER_TYPE_LIMIT = 20


class SearchService:
    """Unified site search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SearchRepository(session)

    async def search(self, term: str, *, type: str = _TYPE_ALL) -> list[SearchResultItem]:
        term = (term or "").strip()
        if not term:
            return []

        results: list[SearchResultItem] = []
        want_article = type in (_TYPE_ALL, _TYPE_ARTICLE)
        want_tool = type in (_TYPE_ALL, _TYPE_TOOL)
        want_user = type in (_TYPE_ALL, _TYPE_USER)

        if want_article:
            for row in await self._repository.search_articles(term, limit=_PER_TYPE_LIMIT):
                results.append(
                    SearchResultItem(
                        resource_type=_TYPE_ARTICLE,
                        id=str(int(row.id)),
                        title=row.title,
                        snippet=row.summary,
                        status=row.status,
                        url=f"/articles/{row.id}",
                    )
                )
        if want_tool:
            for row in await self._repository.search_tools(term, limit=_PER_TYPE_LIMIT):
                results.append(
                    SearchResultItem(
                        resource_type=_TYPE_TOOL,
                        id=str(int(row.id)),
                        title=row.name,
                        snippet=row.summary,
                        status=row.status,
                        url=f"/tools/{row.id}",
                    )
                )
        if want_user:
            for row in await self._repository.search_users(term, limit=_PER_TYPE_LIMIT):
                results.append(
                    SearchResultItem(
                        resource_type=_TYPE_USER,
                        id=str(int(row.id)),
                        title=row.nickname,
                        snippet=row.username,
                        status=row.status,
                        url=f"/users/{row.id}",
                    )
                )
        return results
