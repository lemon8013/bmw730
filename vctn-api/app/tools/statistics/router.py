"""app.tools.statistics — HTTP endpoints.

Read endpoints surface the precomputed rollups; the refresh endpoint recomputes the
popularity ranking. The runtime execution path publishes tool usage through the
outbox, but the rollups are rebuilt on demand here (and may be scheduled later).
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
from app.tools.statistics.schema import (
    StatisticsRefreshRequest,
    StatisticsRefreshResponse,
    ToolPopularityDailyResponse,
    ToolUsageDailyResponse,
)
from app.tools.statistics.service import ToolStatisticsService

router = APIRouter()


def _service(session: DbSessionDep) -> ToolStatisticsService:
    return ToolStatisticsService(session)


@router.get(
    "/statistics/usage-daily",
    response_model=ApiResponse[list[ToolUsageDailyResponse]],
)
async def usage_daily(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    tool_id: str = Query(),
    start: str = Query(description="ISO date, inclusive"),
    end: str = Query(description="ISO date, inclusive"),
) -> ApiResponse[list[ToolUsageDailyResponse]]:
    rows = await _service(session).usage_daily(
        tool_id=int(tool_id),
        start=datetime.date.fromisoformat(start),
        end=datetime.date.fromisoformat(end),
    )
    return success(rows)


@router.get(
    "/statistics/popularity",
    response_model=ApiResponse[list[ToolPopularityDailyResponse]],
)
async def popularity(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    stat_date: str = Query(description="ISO date"),
    window_days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse[list[ToolPopularityDailyResponse]]:
    rows = await _service(session).popularity(
        stat_date=datetime.date.fromisoformat(stat_date),
        window_days=window_days,
        limit=limit,
    )
    return success(rows)


@router.post(
    "/statistics/refresh",
    response_model=ApiResponse[StatisticsRefreshResponse],
    dependencies=[Depends(require_permission("TOOL_MANAGE"))],
)
async def refresh(
    session: DbSessionDep,
    _: AdminPrincipal,
    payload: StatisticsRefreshRequest,
) -> ApiResponse[StatisticsRefreshResponse]:
    return success(
        await _service(session).refresh_popularity(
            stat_date=payload.stat_date, window_days=payload.window_days
        )
    )
