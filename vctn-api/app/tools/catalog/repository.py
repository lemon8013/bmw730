"""app.tools.catalog — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.tools.access.model import ToolAccessPolicy
from app.tools.catalog.model import (
    Tool,
    ToolCategory,
    ToolComponentRegistry,
    ToolVersion,
)

ACTIVE_STATUS: str = "ACTIVE"
PUBLISHED_STATUS: str = "PUBLISHED"


def visibility_condition(subject_type: str, *, default_enabled: bool) -> ColumnElement[bool]:
    """Restrict the catalogue to the tools ``subject_type`` is allowed to see.

    A policy row with ``enabled = false`` hides the tool from that subject. A
    missing row falls back to the configured default visibility: when the
    default denies the subject, only tools carrying an explicit row survive.
    ``tool_id`` is nullable on ``tool_access_policy``, so NULL rows are always
    excluded — a NULL inside ``NOT IN``/``IN`` would swallow every row.
    """
    denied = (
        select(ToolAccessPolicy.tool_id)
        .where(
            ToolAccessPolicy.subject_type == subject_type,
            ToolAccessPolicy.enabled.is_(False),
            ToolAccessPolicy.tool_id.isnot(None),
        )
        .scalar_subquery()
    )
    condition: ColumnElement[bool] = Tool.id.notin_(denied)
    if not default_enabled:
        declared = (
            select(ToolAccessPolicy.tool_id)
            .where(
                ToolAccessPolicy.subject_type == subject_type,
                ToolAccessPolicy.tool_id.isnot(None),
            )
            .scalar_subquery()
        )
        condition = and_(condition, Tool.id.in_(declared))
    return condition


class ToolCatalogRepository:
    """Data access for the tool catalogue."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_categories(self) -> list[ToolCategory]:
        result = await self._session.execute(
            select(ToolCategory)
            .where(ToolCategory.status == ACTIVE_STATUS, ToolCategory.deleted_at.is_(None))
            .order_by(ToolCategory.sort_order, ToolCategory.id)
        )
        return list(result.scalars())

    async def active_tools(
        self, *, subject_type: str, default_enabled: bool
    ) -> list[Tool]:
        result = await self._session.execute(
            select(Tool)
            .where(
                Tool.status == ACTIVE_STATUS,
                Tool.deleted_at.is_(None),
                visibility_condition(subject_type, default_enabled=default_enabled),
            )
            .order_by(Tool.sort_order, Tool.id)
        )
        return list(result.scalars())

    async def get_tool(self, tool_id: int) -> Tool | None:
        result = await self._session.execute(
            select(Tool).where(Tool.id == tool_id, Tool.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_tool_by_slug(self, slug: str) -> Tool | None:
        result = await self._session.execute(
            select(Tool).where(
                func.lower(Tool.slug) == slug.lower(), Tool.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self, keyword: str, *, subject_type: str, default_enabled: bool
    ) -> list[Tool]:
        pattern = f"%{keyword.lower()}%"
        result = await self._session.execute(
            select(Tool)
            .where(
                Tool.status == ACTIVE_STATUS,
                Tool.deleted_at.is_(None),
                visibility_condition(subject_type, default_enabled=default_enabled),
                or_(
                    func.lower(Tool.name).like(pattern),
                    func.lower(Tool.slug).like(pattern),
                    func.lower(func.coalesce(Tool.summary, "")).like(pattern),
                    func.lower(func.coalesce(Tool.description, "")).like(pattern),
                ),
            )
            .order_by(Tool.sort_order, Tool.id)
        )
        return list(result.scalars())

    async def tools_of_category(
        self, category_id: int, *, subject_type: str, default_enabled: bool
    ) -> list[Tool]:
        result = await self._session.execute(
            select(Tool)
            .where(
                Tool.category_id == category_id,
                Tool.status == ACTIVE_STATUS,
                Tool.deleted_at.is_(None),
                visibility_condition(subject_type, default_enabled=default_enabled),
            )
            .order_by(Tool.sort_order, Tool.id)
        )
        return list(result.scalars())

    async def current_version(self, tool: Tool) -> ToolVersion | None:
        if tool.current_version_id is None:
            return None
        return await self._session.get(ToolVersion, int(tool.current_version_id))

    async def versions(self, tool_id: int) -> list[ToolVersion]:
        result = await self._session.execute(
            select(ToolVersion)
            .where(ToolVersion.tool_id == tool_id)
            .order_by(ToolVersion.id.desc())
        )
        return list(result.scalars())

    async def get_version(self, version_id: int) -> ToolVersion | None:
        return await self._session.get(ToolVersion, version_id)

    async def component(self, component_key: str) -> ToolComponentRegistry | None:
        result = await self._session.execute(
            select(ToolComponentRegistry).where(
                ToolComponentRegistry.component_key == component_key
            )
        )
        return result.scalar_one_or_none()

    async def components(self) -> list[ToolComponentRegistry]:
        result = await self._session.execute(
            select(ToolComponentRegistry).order_by(ToolComponentRegistry.component_key)
        )
        return list(result.scalars())

    async def category(self, category_id: int) -> ToolCategory | None:
        return await self._session.get(ToolCategory, category_id)

    async def add_tool(self, **fields: object) -> Tool:
        from app.shared.ids import new_id

        row = Tool(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_version(self, **fields: object) -> ToolVersion:
        from app.shared.ids import new_id

        row = ToolVersion(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_category(self, **fields: object) -> ToolCategory:
        from app.shared.ids import new_id

        row = ToolCategory(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_component(self, **fields: object) -> ToolComponentRegistry:
        from app.shared.ids import new_id

        row = ToolComponentRegistry(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def mark_deleted(self, row: object, *, now: datetime.datetime) -> None:
        row.deleted_at = now
        await self._session.flush()
