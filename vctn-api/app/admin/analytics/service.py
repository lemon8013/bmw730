"""app.admin.analytics — business logic.

Read side over the analytics rollups plus a real recompute of the event daily
rollup. No business logic of the analytics pipeline is re-implemented here.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.analytics.repository import AdminAnalyticsRepository, _day_window
from app.admin.analytics.schema import (
    AnalyticsOverviewResponse,
    EventDailyResponse,
    RecomputeResponse,
    ToolUsageResponse,
)
from app.analytics.statistics.model import BehaviorEventDaily
from app.core.config import Settings, get_settings
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class AdminAnalyticsService:
    """Administrative analytics inspection."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AdminAnalyticsRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def overview(
        self, start: datetime.datetime | None, end: datetime.datetime | None
    ) -> AnalyticsOverviewResponse:
        window_start, window_end = _day_window(start, end)
        data = await self._repository.overview(window_start, window_end)
        return AnalyticsOverviewResponse(**data)  # type: ignore[arg-type]

    async def tool_usage(
        self,
        *,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
        page: PageParams,
    ) -> Page[ToolUsageResponse]:
        window_start, window_end = _day_window(start, end)
        items, total = await self._repository.tool_usage(
            window_start, window_end, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[ToolUsageResponse(**item) for item in items], total=total, params=page
        )

    async def events_daily(
        self,
        *,
        event_code: str | None,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
        page: PageParams,
    ) -> Page[EventDailyResponse]:
        window_start, window_end = _day_window(start, end)
        rows, total = await self._repository.events_daily(
            event_code=event_code,
            start=window_start,
            end=window_end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_event(row) for row in rows], total=total, params=page
        )

    async def recompute(
        self, *, actor_id: int, start: datetime.datetime | None, end: datetime.datetime | None
    ) -> RecomputeResponse:
        window_start, window_end = _day_window(start, end)
        inserted = await self._repository.recompute_events_daily(window_start, window_end)
        await self._audit.record(
            self._session,
            action="ANALYTICS_RECOMPUTE",
            operator_id=int(actor_id),
            resource_type="behavior_event_daily",
            after_data={
                "start": window_start.date().isoformat(),
                "end": window_end.date().isoformat(),
            },
        )
        await write_operation_log(
            self._session,
            operation="ANALYTICS_RECOMPUTE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="behavior_event_daily",
        )
        await self._session.commit()
        return RecomputeResponse(
            start=window_start.date().isoformat(),
            end=window_end.date().isoformat(),
            recomputed_rows=inserted,
        )

    def _to_event(self, row: BehaviorEventDaily) -> EventDailyResponse:
        return EventDailyResponse(
            id=str(int(row.id)),
            stat_date=row.stat_date,
            event_code=str(row.event_code),
            total_count=int(row.total_count or 0),
            unique_user_count=int(row.unique_user_count or 0),
            unique_anonymous_count=int(row.unique_anonymous_count or 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
