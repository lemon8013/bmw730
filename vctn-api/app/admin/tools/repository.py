"""app.admin.tools — data access.

Reuses the :class:`Tool` catalogue and :class:`ToolAccessPolicy` models from the
platform's ``tools`` module. The admin tool management layer is a management
entry point only; it never re-implements tool runtime behaviour.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id
from app.tools.access.model import ToolAccessPolicy
from app.tools.access.service import SUBJECT_GUEST, SUBJECT_USER
from app.tools.catalog.model import Tool
from app.tools.usage.model import ToolUsageEvent


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

    async def list_tools_with_policies(
        self,
    ) -> list[tuple[Tool, ToolAccessPolicy | None, ToolAccessPolicy | None]]:
        """Every tool with its GUEST and USER policy rows, either may be absent."""
        tools = (
            (
                await self._session.execute(
                    select(Tool)
                    .where(Tool.deleted_at.is_(None))
                    .order_by(Tool.sort_order, Tool.id)
                )
            )
            .scalars()
            .all()
        )
        policies = (
            (
                await self._session.execute(
                    select(ToolAccessPolicy).where(ToolAccessPolicy.tool_id.isnot(None))
                )
            )
            .scalars()
            .all()
        )
        by_key: dict[tuple[int, str], ToolAccessPolicy] = {}
        for policy in policies:
            if policy.tool_id is None:
                continue
            by_key[(int(policy.tool_id), str(policy.subject_type))] = policy
        result: list[tuple[Tool, ToolAccessPolicy | None, ToolAccessPolicy | None]] = []
        for tool in tools:
            guest = by_key.get((int(tool.id), SUBJECT_GUEST))
            user = by_key.get((int(tool.id), SUBJECT_USER))
            result.append((tool, guest, user))
        return result

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

    async def upsert_policy(
        self, tool_id: int, subject_type: str, **fields: object
    ) -> ToolAccessPolicy:
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

    async def tool_names(self, tool_ids: list[int]) -> dict[int, tuple[str, str]]:
        """`tool_id -> (name, slug)` for the tools that still exist."""
        if not tool_ids:
            return {}
        rows = (
            await self._session.execute(
                select(Tool.id, Tool.name, Tool.slug).where(Tool.id.in_(tool_ids))
            )
        ).all()
        return {int(row[0]): (str(row[1]), str(row[2])) for row in rows}

    async def usage_by_tool(
        self, *, start: datetime.datetime, end: datetime.datetime
    ) -> list[tuple[int, int, int, int, int, int, datetime.datetime | None]]:
        """Aggregate raw usage events per tool over ``[start, end)``.

        The counts come from ``tool_usage_event``, not from the daily rollup, so
        the answer is correct even when the rollup has never been refreshed.
        """
        total = func.count(ToolUsageEvent.id)
        success = func.coalesce(
            func.sum(sa.case((ToolUsageEvent.success.is_(True), 1), else_=0)), 0
        )
        failure = func.coalesce(
            func.sum(sa.case((ToolUsageEvent.success.is_(False), 1), else_=0)), 0
        )
        rows = (
            await self._session.execute(
                select(
                    ToolUsageEvent.tool_id,
                    total,
                    success,
                    failure,
                    func.count(func.distinct(ToolUsageEvent.user_id)),
                    func.count(func.distinct(ToolUsageEvent.anonymous_id_hash)),
                    func.max(ToolUsageEvent.created_at),
                )
                .where(
                    ToolUsageEvent.tool_id.isnot(None),
                    ToolUsageEvent.created_at >= start,
                    ToolUsageEvent.created_at < end,
                )
                .group_by(ToolUsageEvent.tool_id)
                .order_by(total.desc(), ToolUsageEvent.tool_id)
            )
        ).all()
        return [
            (
                int(row[0]),
                int(row[1] or 0),
                int(row[2] or 0),
                int(row[3] or 0),
                int(row[4] or 0),
                int(row[5] or 0),
                row[6],
            )
            for row in rows
        ]

    async def usage_trend(
        self, *, start: datetime.datetime, end: datetime.datetime
    ) -> list[tuple[datetime.date, int, int, int]]:
        """Platform wide usage per day over ``[start, end)``.

        Days without any event are absent from the result: the report layer
        zero-fills them so the trend line keeps an even time axis.
        """
        day = func.date_trunc("day", ToolUsageEvent.created_at).label("stat_date")
        rows = (
            await self._session.execute(
                select(
                    day,
                    func.count(ToolUsageEvent.id),
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(True), 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(False), 1), else_=0)), 0
                    ),
                )
                .where(
                    ToolUsageEvent.created_at >= start,
                    ToolUsageEvent.created_at < end,
                )
                .group_by(day)
                .order_by(day)
            )
        ).all()
        return [
            (
                row[0].date() if isinstance(row[0], datetime.datetime) else row[0],
                int(row[1] or 0),
                int(row[2] or 0),
                int(row[3] or 0),
            )
            for row in rows
        ]

    async def usage_overview(
        self, *, start: datetime.datetime, end: datetime.datetime
    ) -> tuple[int, int, int, int, int, int, datetime.datetime | None]:
        """Window wide totals: events, successes, failures, users, guests, tools.

        The distinct counts span the whole window, so summing the per tool rows
        would double count anyone who used more than one tool.
        """
        row = (
            await self._session.execute(
                select(
                    func.count(ToolUsageEvent.id),
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(True), 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(False), 1), else_=0)), 0
                    ),
                    func.count(func.distinct(ToolUsageEvent.user_id)),
                    func.count(func.distinct(ToolUsageEvent.anonymous_id_hash)),
                    func.count(func.distinct(ToolUsageEvent.tool_id)),
                    func.max(ToolUsageEvent.created_at),
                ).where(
                    ToolUsageEvent.created_at >= start,
                    ToolUsageEvent.created_at < end,
                )
            )
        ).one()
        return (
            int(row[0] or 0),
            int(row[1] or 0),
            int(row[2] or 0),
            int(row[3] or 0),
            int(row[4] or 0),
            int(row[5] or 0),
            row[6],
        )

    async def usage_daily(
        self, *, tool_id: int, start: datetime.datetime, end: datetime.datetime
    ) -> list[tuple[datetime.date, int, int, int]]:
        """Per day usage counts for one tool over ``[start, end)``."""
        day = func.date_trunc("day", ToolUsageEvent.created_at).label("stat_date")
        total = func.count(ToolUsageEvent.id)
        rows = (
            await self._session.execute(
                select(
                    day,
                    total,
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(True), 1), else_=0)), 0
                    ),
                    func.coalesce(
                        func.sum(sa.case((ToolUsageEvent.success.is_(False), 1), else_=0)), 0
                    ),
                )
                .where(
                    ToolUsageEvent.tool_id == tool_id,
                    ToolUsageEvent.created_at >= start,
                    ToolUsageEvent.created_at < end,
                )
                .group_by(day)
                .order_by(day)
            )
        ).all()
        return [
            (
                row[0].date() if isinstance(row[0], datetime.datetime) else row[0],
                int(row[1] or 0),
                int(row[2] or 0),
                int(row[3] or 0),
            )
            for row in rows
        ]

    async def flush(self) -> None:
        await self._session.flush()
