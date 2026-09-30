"""app.tools.usage — HTTP endpoints.

Read paths use :class:`app.tools.usage.repository.ToolUsageRepository` directly
(the read side of usage is intentionally outside the write service so the
analytics read model cannot block a write). The daily popularity rollup is the one
write path exposed here and it delegates to the existing
:class:`app.tools.usage.service.ToolUsageService`.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    PlatformPrincipal,
    require_permission,
)
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.statistics.model import ToolUsageDaily
from app.tools.usage.repository import ToolUsageRepository
from app.tools.usage.schema import (
    PopularityRefreshRequest,
    PopularityRefreshResponse,
    ToolPopularityDailyResponse,
    ToolRecentUsageResponse,
    ToolUsageDailyResponse,
    ToolUsageSummary,
)
from app.tools.usage.service import ToolUsageService

router = APIRouter()


def _usage_repository(session: DbSessionDep) -> ToolUsageRepository:
    return ToolUsageRepository(session)


def _to_daily(row: ToolUsageDaily) -> ToolUsageDailyResponse:
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


@router.get("/usage/recent", response_model=ApiResponse[list[ToolRecentUsageResponse]])
async def usage_recent(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    user_id: str | None = Query(default=None, description="Admin override; defaults to caller"),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[ToolRecentUsageResponse]]:
    resolved_user = int(user_id) if user_id else principal.subject_id
    rows = await _usage_repository(session).recent(user_id=resolved_user, limit=limit)
    return success(
        [
            ToolRecentUsageResponse(
                id=str(int(row.id)),
                user_id=None if row.user_id is None else str(int(row.user_id)),
                tool_id=None if row.tool_id is None else str(int(row.tool_id)),
                last_used_at=row.last_used_at,
                use_count=int(row.use_count or 0),
            )
            for row in rows
        ]
    )


@router.get("/usage/daily", response_model=ApiResponse[list[ToolUsageDailyResponse]])
async def usage_daily(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    tool_id: str = Query(),
    start: str = Query(description="ISO date, inclusive"),
    end: str = Query(description="ISO date, inclusive"),
) -> ApiResponse[list[ToolUsageDailyResponse]]:
    rows = await _usage_repository(session).usage_daily(
        tool_id=int(tool_id),
        start=datetime.date.fromisoformat(start),
        end=datetime.date.fromisoformat(end),
    )
    return success([_to_daily(row) for row in rows])


@router.get("/usage/popularity", response_model=ApiResponse[list[ToolPopularityDailyResponse]])
async def usage_popularity(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    stat_date: str = Query(description="ISO date"),
    window_days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse[list[ToolPopularityDailyResponse]]:
    rows = await _usage_repository(session).popularity(
        stat_date=datetime.date.fromisoformat(stat_date),
        window_days=window_days,
        limit=limit,
    )
    return success(
        [
            ToolPopularityDailyResponse(
                id=str(int(row.id)),
                stat_date=row.stat_date,
                window_days=int(row.window_days),
                tool_id=None if row.tool_id is None else str(int(row.tool_id)),
                usage_count=int(row.usage_count or 0),
                unique_user_count=int(row.unique_user_count or 0),
                rank_no=row.rank_no,
                score=None if row.score is None else float(row.score),
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


@router.get("/usage/summary", response_model=ApiResponse[ToolUsageSummary])
async def usage_summary(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    tool_id: str = Query(),
    start: str = Query(description="ISO date, inclusive"),
    end: str = Query(description="ISO date, inclusive"),
) -> ApiResponse[ToolUsageSummary]:
    start_date = datetime.date.fromisoformat(start)
    end_date = datetime.date.fromisoformat(end)
    window_start = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=datetime.UTC)
    window_end = (
        datetime.datetime.combine(end_date, datetime.time.min, tzinfo=datetime.UTC)
        + datetime.timedelta(days=1)
    )
    total, success_count, failure_count, unique_users = await _usage_repository(
        session
    ).counts_for_tool(int(tool_id), start=window_start, end=window_end)
    daily_rows = await _usage_repository(session).usage_daily(
        tool_id=int(tool_id), start=start_date, end=end_date
    )
    avg = None
    if daily_rows:
        summed = sum(
            float(r.avg_duration_ms) * (int(r.total_count) or 0)
            for r in daily_rows
            if r.avg_duration_ms is not None
        )
        total_count = sum(int(r.total_count) or 0 for r in daily_rows)
        avg = round(summed / total_count, 2) if total_count else None
    return success(
        ToolUsageSummary(
            tool_id=tool_id,
            period_start=window_start,
            period_end=window_end,
            total_executions=int(total),
            success_count=int(success_count),
            failure_count=int(failure_count),
            unique_users=int(unique_users),
            avg_duration_ms=avg,
        )
    )


@router.post(
    "/usage/refresh-popularity",
    response_model=ApiResponse[PopularityRefreshResponse],
    dependencies=[Depends(require_permission("TOOL_MANAGE"))],
)
async def refresh_popularity(
    session: DbSessionDep,
    _: AdminPrincipal,
    payload: PopularityRefreshRequest,
) -> ApiResponse[PopularityRefreshResponse]:
    refreshed = await ToolUsageService(session).refresh_popularity(
        stat_date=payload.stat_date, window_days=payload.window_days
    )
    return success(
        PopularityRefreshResponse(
            stat_date=payload.stat_date,
            window_days=payload.window_days,
            refreshed=int(refreshed),
        )
    )
