"""app.analytics.statistics — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.statistics.model import (
    BehaviorEventDaily,
    BehaviorFunnel,
    BehaviorPageDaily,
    BehaviorSearchDaily,
    BehaviorToolDaily,
    BehaviorUserDaily,
)
from app.analytics.statistics.repository import BehaviorStatisticsRepository
from app.analytics.statistics.schema import (
    EventDailyResponse,
    FunnelCreateRequest,
    FunnelResponse,
    FunnelUpdateRequest,
    PageDailyResponse,
    RecomputeRequest,
    SearchDailyResponse,
    ToolDailyResponse,
    UserDailyResponse,
)
from app.core.config import Settings, get_settings
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


def _to_event_daily(row: BehaviorEventDaily) -> EventDailyResponse:
    return EventDailyResponse(
        id=str(int(row.id)),
        stat_date=row.stat_date,
        event_code=row.event_code,
        total_count=int(row.total_count),
        unique_user_count=int(row.unique_user_count),
        unique_anonymous_count=int(row.unique_anonymous_count),
        updated_at=row.updated_at,
    )


def _to_user_daily(row: BehaviorUserDaily) -> UserDailyResponse:
    return UserDailyResponse(
        id=str(int(row.id)),
        stat_date=row.stat_date,
        user_id=None if row.user_id is None else str(int(row.user_id)),
        anonymous_id_hash=row.anonymous_id_hash,
        event_count=int(row.event_count),
        active=bool(row.active),
        first_event_at=row.first_event_at,
        last_event_at=row.last_event_at,
    )


def _to_page_daily(row: BehaviorPageDaily) -> PageDailyResponse:
    return PageDailyResponse(
        id=str(int(row.id)),
        stat_date=row.stat_date,
        page_code=row.page_code,
        view_count=int(row.view_count),
        unique_user_count=int(row.unique_user_count),
        unique_anonymous_count=int(row.unique_anonymous_count),
        avg_duration_ms=None if row.avg_duration_ms is None else float(row.avg_duration_ms),
    )


def _to_tool_daily(row: BehaviorToolDaily) -> ToolDailyResponse:
    return ToolDailyResponse(
        id=str(int(row.id)),
        stat_date=row.stat_date,
        tool_id=None if row.tool_id is None else str(int(row.tool_id)),
        view_count=int(row.view_count),
        start_count=int(row.start_count),
        execute_count=int(row.execute_count),
        success_count=int(row.success_count),
        failure_count=int(row.failure_count),
        copy_count=int(row.copy_count),
        download_count=int(row.download_count),
        unique_user_count=int(row.unique_user_count),
    )


def _to_search_daily(row: BehaviorSearchDaily) -> SearchDailyResponse:
    return SearchDailyResponse(
        id=str(int(row.id)),
        stat_date=row.stat_date,
        search_type=row.search_type,
        keyword_hash=row.keyword_hash,
        search_count=int(row.search_count),
        result_click_count=int(row.result_click_count),
    )


def _to_funnel(row: BehaviorFunnel) -> FunnelResponse:
    return FunnelResponse(
        id=str(int(row.id)),
        funnel_code=row.funnel_code,
        funnel_name=row.funnel_name,
        step_no=int(row.step_no),
        step_code=row.step_code,
        event_code=row.event_code,
        enabled=bool(row.enabled),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class BehaviorStatisticsService:
    """Serve the rolled-up behaviour tables and maintain funnel definitions."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = BehaviorStatisticsRepository(session)
        self._settings = settings or get_settings()

    async def event_daily(
        self, *, start_date=None, end_date=None, event_code=None, page: PageParams
    ) -> Page[EventDailyResponse]:
        rows, total = await self._repository.list_event_daily(
            start_date=start_date,
            end_date=end_date,
            event_code=event_code,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_event_daily(r) for r in rows], total=total, params=page
        )

    async def user_daily(
        self, *, start_date=None, end_date=None, user_id=None, page: PageParams
    ) -> Page[UserDailyResponse]:
        rows, total = await self._repository.list_user_daily(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_user_daily(r) for r in rows], total=total, params=page
        )

    async def page_daily(
        self, *, start_date=None, end_date=None, page_code=None, page: PageParams
    ) -> Page[PageDailyResponse]:
        rows, total = await self._repository.list_page_daily(
            start_date=start_date,
            end_date=end_date,
            page_code=page_code,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_page_daily(r) for r in rows], total=total, params=page
        )

    async def tool_daily(
        self, *, start_date=None, end_date=None, tool_id=None, page: PageParams
    ) -> Page[ToolDailyResponse]:
        rows, total = await self._repository.list_tool_daily(
            start_date=start_date,
            end_date=end_date,
            tool_id=tool_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_tool_daily(r) for r in rows], total=total, params=page
        )

    async def search_daily(
        self, *, start_date=None, end_date=None, search_type=None, page: PageParams
    ) -> Page[SearchDailyResponse]:
        rows, total = await self._repository.list_search_daily(
            start_date=start_date,
            end_date=end_date,
            search_type=search_type,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_search_daily(r) for r in rows], total=total, params=page
        )

    async def list_funnels(self, *, enabled_only: bool = False) -> list[FunnelResponse]:
        rows = await self._repository.list_funnels(enabled_only=enabled_only)
        return [_to_funnel(r) for r in rows]

    async def create_funnel(
        self, req: FunnelCreateRequest, *, operator_id: int | None = None
    ) -> FunnelResponse:
        row = await self._repository.add_funnel(
            funnel_code=req.funnel_code,
            funnel_name=req.funnel_name,
            step_no=req.step_no,
            step_code=req.step_code,
            event_code=req.event_code,
            enabled=req.enabled,
        )
        await write_operation_log(
            self._session,
            operation="ANALYTICS_FUNNEL_CREATE",
            result=RESULT_SUCCESS,
            operator_id=operator_id,
            resource_type="behavior_funnel",
            resource_id=str(int(row.id)),
            metadata={"funnel_code": req.funnel_code, "step_no": req.step_no},
        )
        await self._session.commit()
        return _to_funnel(row)

    async def update_funnel(
        self,
        funnel_id: int,
        req: FunnelUpdateRequest,
        *,
        operator_id: int | None = None,
    ) -> FunnelResponse | None:
        row = await self._repository.update_funnel(
            funnel_id,
            funnel_name=req.funnel_name,
            step_no=req.step_no,
            step_code=req.step_code,
            event_code=req.event_code,
            enabled=req.enabled,
        )
        if row is None:
            return None
        await write_operation_log(
            self._session,
            operation="ANALYTICS_FUNNEL_UPDATE",
            result=RESULT_SUCCESS,
            operator_id=operator_id,
            resource_type="behavior_funnel",
            resource_id=str(funnel_id),
            metadata={"step_no": req.step_no},
        )
        await self._session.commit()
        return _to_funnel(row)

    async def delete_funnel(
        self, funnel_id: int, *, operator_id: int | None = None
    ) -> bool:
        removed = await self._repository.delete_funnel(funnel_id)
        if removed:
            await write_operation_log(
                self._session,
                operation="ANALYTICS_FUNNEL_DELETE",
                result=RESULT_SUCCESS,
                operator_id=operator_id,
                resource_type="behavior_funnel",
                resource_id=str(funnel_id),
            )
            await self._session.commit()
        return removed

    async def recompute(
        self, req: RecomputeRequest, *, operator_id: int | None = None
    ) -> dict[str, int]:
        """Rebuild every ``*_daily`` table from ``behavior_event``."""
        today = datetime.datetime.now(datetime.UTC).date()
        end_date = req.end_date or today
        start_date = req.start_date or (end_date - datetime.timedelta(days=6))
        # Bound the work window so a missing range cannot rebuild the world.
        if (end_date - start_date).days > 90:
            start_date = end_date - datetime.timedelta(days=90)

        start = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=datetime.UTC)
        end = datetime.datetime.combine(
            end_date, datetime.time.min, tzinfo=datetime.UTC
        ) + datetime.timedelta(days=1)

        counts: dict[str, int] = {}
        counts["event_daily"] = await self._repository.recompute_event_daily(start, end)
        counts["user_daily"] = await self._repository.recompute_user_daily(start, end)
        counts["page_daily"] = await self._repository.recompute_page_daily(start, end)
        counts["tool_daily"] = await self._repository.recompute_tool_daily(start, end)
        counts["search_daily"] = await self._repository.recompute_search_daily(start, end)

        await write_operation_log(
            self._session,
            operation="ANALYTICS_RECOMPUTE",
            result=RESULT_SUCCESS,
            operator_id=operator_id,
            resource_type="behavior_event",
            metadata={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                **counts,
            },
        )
        await self._session.commit()
        return counts
