"""app.tools.statistics — business logic.

A thin service over the statistics repository. The only write path is
``refresh_popularity`` which performs the real aggregation; every other method is a
read that returns the precomputed rollups.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.tools.statistics.model import ToolPopularityDaily, ToolUsageDaily
from app.tools.statistics.repository import ToolStatisticsRepository
from app.tools.statistics.schema import (
    StatisticsRefreshResponse,
    ToolPopularityDailyResponse,
    ToolUsageDailyResponse,
)


class ToolStatisticsService:
    """Tool usage statistics."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ToolStatisticsRepository(session)
        self._settings = settings or get_settings()

    async def usage_daily(
        self, *, tool_id: int, start: datetime.date, end: datetime.date
    ) -> list[ToolUsageDailyResponse]:
        rows = await self._repository.usage_daily(tool_id=tool_id, start=start, end=end)
        return [self._to_daily(row) for row in rows]

    async def popularity(
        self, *, stat_date: datetime.date, window_days: int, limit: int | None = None
    ) -> list[ToolPopularityDailyResponse]:
        rows = await self._repository.popularity(
            stat_date=stat_date, window_days=window_days, limit=limit
        )
        return [self._to_popularity(row) for row in rows]

    async def refresh_popularity(
        self, *, stat_date: datetime.date, window_days: int
    ) -> StatisticsRefreshResponse:
        refreshed = await self._repository.refresh_popularity(
            stat_date=stat_date, window_days=window_days
        )
        await self._session.commit()
        return StatisticsRefreshResponse(
            stat_date=stat_date, window_days=window_days, refreshed=int(refreshed)
        )

    def _to_daily(self, row: ToolUsageDaily) -> ToolUsageDailyResponse:
        return ToolUsageDailyResponse(
            id=str(int(row.id)),
            stat_date=row.stat_date,
            tool_id=None if row.tool_id is None else str(int(row.tool_id)),
            total_count=int(row.total_count or 0),
            success_count=int(row.success_count or 0),
            failure_count=int(row.failure_count or 0),
            guest_count=int(row.guest_count or 0),
            user_count=int(row.user_count or 0),
            unique_user_count=int(row.unique_user_count or 0),
            unique_guest_count=int(row.unique_guest_count or 0),
            avg_duration_ms=None if row.avg_duration_ms is None else float(row.avg_duration_ms),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_popularity(self, row: ToolPopularityDaily) -> ToolPopularityDailyResponse:
        r = row
        return ToolPopularityDailyResponse(
            id=str(int(r.id)),
            stat_date=r.stat_date,
            window_days=int(r.window_days),
            tool_id=None if r.tool_id is None else str(int(r.tool_id)),
            usage_count=int(r.usage_count or 0),
            unique_user_count=int(r.unique_user_count or 0),
            rank_no=r.rank_no,
            score=None if r.score is None else float(r.score),
            created_at=r.created_at,
        )
