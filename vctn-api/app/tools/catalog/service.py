"""app.tools.catalog — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.tools.catalog.model import Tool, ToolCategory, ToolVersion
from app.tools.catalog.repository import ToolCatalogRepository
from app.tools.catalog.schema import (
    ToolCategoryResponse,
    ToolResponse,
    ToolVersionResponse,
)
from app.tools.usage.repository import ToolUsageRepository


class ToolCatalogService:
    """Read side of the tool catalogue."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ToolCatalogRepository(session)
        self._usage = ToolUsageRepository(session)
        self._settings = settings or get_settings()

    async def categories(self) -> list[ToolCategoryResponse]:
        rows = await self._repository.active_categories()
        return [self._to_category(row) for row in rows]

    async def list_tools(self, category_id: int | None = None) -> list[ToolResponse]:
        rows = (
            await self._repository.tools_of_category(category_id)
            if category_id is not None
            else await self._repository.active_tools()
        )
        return [self._to_tool(row) for row in rows]

    async def get_tool(self, tool_id: int) -> ToolResponse:
        row = await self._repository.get_tool(tool_id)
        if row is None:
            raise NotFoundError("tool not found")
        return self._to_tool(row)

    async def get_by_slug(self, slug: str) -> ToolResponse:
        row = await self._repository.get_tool_by_slug(slug)
        if row is None:
            raise NotFoundError("tool not found")
        return self._to_tool(row)

    async def search(self, keyword: str) -> list[ToolResponse]:
        rows = await self._repository.search(keyword)
        return [self._to_tool(row) for row in rows]

    async def popular(self, *, window_days: int = 7, limit: int = 20) -> list[dict]:
        """Return the popularity ranking.

        ``usage_count`` counts executions, ``unique_user_count`` counts distinct
        users: the two numbers answer different questions and are never mixed.
        """
        today = datetime.datetime.now(datetime.UTC).date()
        rows = await self._usage.popularity(stat_date=today, window_days=window_days, limit=limit)
        result: list[dict] = []
        for row in rows:
            tool = await self._repository.get_tool(int(row.tool_id))
            result.append(
                {
                    "tool_id": str(int(row.tool_id)),
                    "tool_name": None if tool is None else str(tool.name),
                    "tool_slug": None if tool is None else str(tool.slug),
                    "usage_count": int(row.usage_count or 0),
                    "unique_user_count": int(row.unique_user_count or 0),
                    "rank_no": row.rank_no,
                    "score": None if row.score is None else float(row.score),
                }
            )
        return result

    async def recent(self, user_id: int, *, limit: int = 20) -> list[dict]:
        rows = await self._usage.recent(user_id=user_id, limit=limit)
        result: list[dict] = []
        for row in rows:
            tool = await self._repository.get_tool(int(row.tool_id))
            result.append(
                {
                    "tool_id": str(int(row.tool_id)),
                    "tool_name": None if tool is None else str(tool.name),
                    "tool_slug": None if tool is None else str(tool.slug),
                    "last_used_at": row.last_used_at,
                    "use_count": int(row.use_count or 0),
                }
            )
        return result

    async def versions(self, tool_id: int) -> list[ToolVersionResponse]:
        rows = await self._repository.versions(tool_id)
        return [self._to_version(row) for row in rows]

    def _to_category(self, row: ToolCategory) -> ToolCategoryResponse:
        return ToolCategoryResponse(
            id=str(int(row.id)),
            category_code=str(row.category_code),
            category_name=str(row.category_name),
            description=row.description,
            icon_url=row.icon_url,
            sort_order=int(row.sort_order or 0),
            status=str(row.status),
        )

    def _to_tool(self, row: Tool) -> ToolResponse:
        keywords = row.keywords or []
        tags = row.tags or []
        return ToolResponse(
            id=str(int(row.id)),
            code=str(row.code),
            name=str(row.name),
            slug=str(row.slug),
            category_id=None if row.category_id is None else str(int(row.category_id)),
            icon=row.icon,
            summary=row.summary,
            description=row.description,
            keywords=[str(item) for item in keywords],
            tags=[str(item) for item in tags],
            component_key=str(row.component_key),
            execution_mode=str(row.execution_mode),
            status=str(row.status),
            sort_order=int(row.sort_order or 0),
            current_version_id=(
                None if row.current_version_id is None else str(int(row.current_version_id))
            ),
        )

    def _to_version(self, row: ToolVersion) -> ToolVersionResponse:
        return ToolVersionResponse(
            id=str(int(row.id)),
            tool_id=str(int(row.tool_id)),
            version=str(row.version),
            release_status=str(row.release_status),
            changelog=row.changelog,
            runtime_config=row.runtime_config,
            published_at=row.published_at,
        )
