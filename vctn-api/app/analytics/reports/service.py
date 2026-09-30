"""app.analytics.reports — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.reports.repository import AnalyticsReportRepository
from app.analytics.reports.schema import (
    FunnelStepSummary,
    FunnelSummaryItem,
    OverviewResponse,
    ToolRankingItem,
    TrendPoint,
    TrendResponse,
)
from app.analytics.statistics.model import BehaviorFunnel
from app.core.config import Settings, get_settings


class AnalyticsReportService:
    """Build analytics report views from the rolled-up tables."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AnalyticsReportRepository(session)
        self._settings = settings or get_settings()

    async def overview(
        self, *, start_date: datetime.date, end_date: datetime.date, limit: int = 10
    ) -> OverviewResponse:
        pv, uv, active_users = await self._repository.overview_counts(start_date, end_date)
        ranked = await self._repository.tool_ranking(start_date, end_date, limit)
        tool_top = [
            ToolRankingItem(
                tool_id=None if item["tool_id"] is None else str(item["tool_id"]),
                execute_count=item["execute_count"],
                success_count=item["success_count"],
                failure_count=item["failure_count"],
                unique_user_count=item["unique_user_count"],
            )
            for item in ranked
        ]
        return OverviewResponse(
            pv=pv,
            uv=uv,
            active_users=active_users,
            tool_top=tool_top,
            generated_at=datetime.datetime.now(datetime.UTC),
        )

    async def trends(
        self, *, start_date: datetime.date, end_date: datetime.date
    ) -> TrendResponse:
        points = await self._repository.trend_points(start_date, end_date)
        return TrendResponse(
            start_date=start_date,
            end_date=end_date,
            points=[
                TrendPoint(
                    stat_date=item["stat_date"], pv=item["pv"], uv=item["uv"]
                )
                for item in points
            ],
        )

    async def tool_rankings(
        self, *, start_date: datetime.date, end_date: datetime.date, limit: int = 20
    ) -> list[ToolRankingItem]:
        ranked = await self._repository.tool_ranking(start_date, end_date, limit)
        return [
            ToolRankingItem(
                tool_id=None if item["tool_id"] is None else str(item["tool_id"]),
                execute_count=item["execute_count"],
                success_count=item["success_count"],
                failure_count=item["failure_count"],
                unique_user_count=item["unique_user_count"],
            )
            for item in ranked
        ]

    async def funnel_summary(
        self, *, start_date: datetime.date, end_date: datetime.date
    ) -> list[FunnelSummaryItem]:
        funnels = await self._repository.enabled_funnels()
        # Group the flat step rows by funnel_code, keeping insertion order.
        grouped: dict[str, list[BehaviorFunnel]] = {}
        for funnel in funnels:
            grouped.setdefault(funnel.funnel_code, []).append(funnel)

        summary: list[FunnelSummaryItem] = []
        for funnel_code, steps_rows in grouped.items():
            steps_rows.sort(key=lambda item: item.step_no)
            steps: list[FunnelStepSummary] = []
            first_step_count: int | None = None
            for row in steps_rows:
                step_count = await self._repository.funnel_step_count(
                    row.event_code, start_date, end_date
                )
                if first_step_count is None:
                    first_step_count = step_count
                steps.append(
                    FunnelStepSummary(
                        step_no=int(row.step_no),
                        step_code=row.step_code,
                        event_code=row.event_code,
                        enabled=bool(row.enabled),
                        event_count=step_count,
                    )
                )
            summary.append(
                FunnelSummaryItem(
                    funnel_code=funnel_code,
                    funnel_name=steps_rows[0].funnel_name,
                    first_step_count=int(first_step_count or 0),
                    steps=steps,
                )
            )
        return summary
