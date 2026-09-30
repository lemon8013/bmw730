"""app.tools.usage — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.statistics.model import ToolPopularityDaily, ToolUsageDaily
from app.tools.usage.model import ToolRecentUsage, ToolUsageEvent


class ToolUsageRepository:
    """Data access for tool usage events, daily rollups and popularity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_event(self, **fields: object) -> ToolUsageEvent:
        from app.shared.ids import new_id

        row = ToolUsageEvent(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def recent(self, *, user_id: int, limit: int) -> list[ToolRecentUsage]:
        result = await self._session.execute(
            select(ToolRecentUsage)
            .where(ToolRecentUsage.user_id == user_id)
            .order_by(ToolRecentUsage.last_used_at.desc(), ToolRecentUsage.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def recent_row(self, *, user_id: int, tool_id: int) -> ToolRecentUsage | None:
        result = await self._session.execute(
            select(ToolRecentUsage).where(
                ToolRecentUsage.user_id == user_id, ToolRecentUsage.tool_id == tool_id
            )
        )
        return result.scalar_one_or_none()

    async def add_recent(self, **fields: object) -> ToolRecentUsage:
        from app.shared.ids import new_id

        row = ToolRecentUsage(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def popularity(
        self, *, stat_date: datetime.date, window_days: int, limit: int
    ) -> list[ToolPopularityDaily]:
        result = await self._session.execute(
            select(ToolPopularityDaily)
            .where(
                ToolPopularityDaily.stat_date == stat_date,
                ToolPopularityDaily.window_days == window_days,
            )
            .order_by(ToolPopularityDaily.rank_no, ToolPopularityDaily.id)
            .limit(limit)
        )
        return list(result.scalars())

    async def usage_daily(
        self, *, tool_id: int, start: datetime.date, end: datetime.date
    ) -> list[ToolUsageDaily]:
        result = await self._session.execute(
            select(ToolUsageDaily)
            .where(
                ToolUsageDaily.tool_id == tool_id,
                ToolUsageDaily.stat_date >= start,
                ToolUsageDaily.stat_date <= end,
            )
            .order_by(ToolUsageDaily.stat_date)
        )
        return list(result.scalars())

    async def rollup_row_for_update(
        self, *, tool_id: int, stat_date: datetime.date
    ) -> ToolUsageDaily | None:
        result = await self._session.execute(
            select(ToolUsageDaily)
            .where(
                ToolUsageDaily.tool_id == tool_id, ToolUsageDaily.stat_date == stat_date
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_rollup(self, **fields: object) -> ToolUsageDaily:
        from app.shared.ids import new_id

        row = ToolUsageDaily(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def popularity_row(
        self, *, tool_id: int, stat_date: datetime.date, window_days: int
    ) -> ToolPopularityDaily | None:
        result = await self._session.execute(
            select(ToolPopularityDaily).where(
                ToolPopularityDaily.tool_id == tool_id,
                ToolPopularityDaily.stat_date == stat_date,
                ToolPopularityDaily.window_days == window_days,
            )
        )
        return result.scalar_one_or_none()

    async def create_popularity(self, **fields: object) -> ToolPopularityDaily:
        from app.shared.ids import new_id

        row = ToolPopularityDaily(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def counts_for_tool(
        self, tool_id: int, *, start: datetime.datetime, end: datetime.datetime
    ) -> tuple[int, int, int, int]:
        """Return ``(total, success, failure, unique_users)`` for a window."""
        row = (
            await self._session.execute(
                select(
                    func.count(ToolUsageEvent.id),
                    func.count(ToolUsageEvent.id).filter(ToolUsageEvent.success.is_(True)),
                    func.count(ToolUsageEvent.id).filter(ToolUsageEvent.success.is_(False)),
                    func.count(func.distinct(ToolUsageEvent.user_id)),
                ).where(
                    ToolUsageEvent.tool_id == tool_id,
                    ToolUsageEvent.created_at >= start,
                    ToolUsageEvent.created_at < end,
                )
            )
        ).one()
        total = int(row[0] or 0)
        success = int(row[1] or 0)
        failure = int(row[2] or 0)
        unique_users = int(row[3] or 0)
        return total, success, failure, unique_users
