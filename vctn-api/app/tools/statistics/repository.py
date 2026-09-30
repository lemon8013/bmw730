"""app.tools.statistics — data access.

Reads come straight from the ``tool_usage_daily`` / ``tool_popularity_daily``
rollups. ``refresh_popularity`` is the one writer: it recomputes the ranking from
the raw ``tool_usage_event`` stream for a window and upserts the
``tool_popularity_daily`` rows — a real aggregation, not a stub.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id
from app.tools.statistics.model import ToolPopularityDaily, ToolUsageDaily


class ToolStatisticsRepository:
    """Data access for tool usage statistics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

    async def popularity(
        self, *, stat_date: datetime.date, window_days: int, limit: int | None = None
    ) -> list[ToolPopularityDaily]:
        stmt = (
            select(ToolPopularityDaily)
            .where(
                ToolPopularityDaily.stat_date == stat_date,
                ToolPopularityDaily.window_days == window_days,
            )
            .order_by(ToolPopularityDaily.rank_no, ToolPopularityDaily.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars())

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

    async def upsert_popularity(
        self,
        *,
        stat_date: datetime.date,
        window_days: int,
        tool_id: int,
        usage_count: int,
        unique_user_count: int,
        rank_no: int,
        score: float,
    ) -> ToolPopularityDaily:
        row = await self.popularity_row(
            tool_id=tool_id, stat_date=stat_date, window_days=window_days
        )
        if row is None:
            row = ToolPopularityDaily(
                id=new_id(),
                stat_date=stat_date,
                window_days=window_days,
                tool_id=tool_id,
                usage_count=usage_count,
                unique_user_count=unique_user_count,
                rank_no=rank_no,
                score=score,
            )
            self._session.add(row)
        else:
            row.usage_count = usage_count
            row.unique_user_count = unique_user_count
            row.rank_no = rank_no
            row.score = score
        await self._session.flush()
        return row

    async def refresh_popularity(
        self, *, stat_date: datetime.date, window_days: int
    ) -> int:
        """Recompute and persist the popularity ranking for one window.

        Executions and distinct users are counted separately so the ranking is
        driven by executions, never by a mixed number.
        """
        from app.tools.catalog.repository import ToolCatalogRepository
        from app.tools.usage.repository import ToolUsageRepository

        catalog = ToolCatalogRepository(self._session)
        usage = ToolUsageRepository(self._session)
        tools = await catalog.active_tools()
        start = stat_date - datetime.timedelta(days=window_days - 1)
        window_start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.UTC)
        window_end = window_start + datetime.timedelta(days=window_days)

        scored: list[tuple[int, int, int]] = []
        for tool in tools:
            total, _success, _failure, unique_users = await usage.counts_for_tool(
                int(tool.id), start=window_start, end=window_end
            )
            scored.append((int(tool.id), int(total), int(unique_users)))
        scored.sort(key=lambda item: (-item[1], item[0]))

        for rank, (tool_id, usage_count, unique_users) in enumerate(scored, start=1):
            await self.upsert_popularity(
                stat_date=stat_date,
                window_days=window_days,
                tool_id=tool_id,
                usage_count=usage_count,
                unique_user_count=unique_users,
                rank_no=rank,
                score=float(usage_count),
            )
        return len(scored)
