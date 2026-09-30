"""app.admin.tools — data access.

Reuses the :class:`Tool` catalogue and :class:`ToolAccessPolicy` models from the
platform's ``tools`` module. The admin tool management layer is a management
entry point only; it never re-implements tool runtime behaviour.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id
from app.tools.access.model import ToolAccessPolicy
from app.tools.catalog.model import Tool


class AdminToolRepository:
    """Data access for administrative tool management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tools(
        self,
        *,
        status: str | None,
        category_id: int | None,
        keyword: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Tool], int]:
        conditions: list[object] = [Tool.deleted_at.is_(None)]
        if status:
            conditions.append(Tool.status == status)
        if category_id is not None:
            conditions.append(Tool.category_id == category_id)
        if keyword:
            pattern = f"%{keyword.lower()}%"
            conditions.append(
                or_(
                    func.lower(Tool.name).like(pattern),
                    func.lower(Tool.code).like(pattern),
                    func.lower(Tool.slug).like(pattern),
                )
            )
        total = int(
            (
                await self._session.execute(
                    select(func.count(Tool.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(Tool)
                    .where(*conditions)
                    .order_by(Tool.sort_order, Tool.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_tool(self, tool_id: int) -> Tool | None:
        result = await self._session.execute(
            select(Tool).where(Tool.id == tool_id, Tool.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_tool(self, **fields: object) -> Tool:
        row = Tool(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_tool(self, row: Tool, **fields: object) -> Tool:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()
        return row

    async def list_policies(self) -> list[tuple[ToolAccessPolicy, str | None]]:
        result = await self._session.execute(
            select(ToolAccessPolicy, Tool.name)
            .join(Tool, Tool.id == ToolAccessPolicy.tool_id, isouter=True)
            .order_by(ToolAccessPolicy.tool_id, ToolAccessPolicy.subject_type)
        )
        return list(result.all())

    async def policy_for(
        self, tool_id: int, subject_type: str
    ) -> ToolAccessPolicy | None:
        result = await self._session.execute(
            select(ToolAccessPolicy).where(
                ToolAccessPolicy.tool_id == tool_id,
                ToolAccessPolicy.subject_type == subject_type,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_policy(self, tool_id: int, subject_type: str, **fields: object) -> ToolAccessPolicy:
        existing = await self.policy_for(tool_id, subject_type)
        if existing is not None:
            for key, value in fields.items():
                setattr(existing, key, value)
            await self._session.flush()
            return existing
        row = ToolAccessPolicy(id=new_id(), tool_id=tool_id, subject_type=subject_type, **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def flush(self) -> None:
        await self._session.flush()
