"""app.analytics.reports — HTTP endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.analytics.reports.schema import (
    FunnelSummaryItem,
    OverviewResponse,
    ToolRankingItem,
    TrendResponse,
)
from app.analytics.reports.service import AnalyticsReportService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()

_VIEW = Depends(require_permission("ANALYTICS_VIEW"))


def _resolve_window(
    start_date: datetime.date | None, end_date: datetime.date | None
) -> tuple[datetime.date, datetime.date]:
    today = datetime.datetime.now(datetime.UTC).date()
    end = end_date or today
    start = start_date or (end - datetime.timedelta(days=29))
    return start, end


@router.get("/overview", response_model=ApiResponse[OverviewResponse])
async def overview(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> ApiResponse[OverviewResponse]:
    start, end = _resolve_window(start_date, end_date)
    return success(
        await AnalyticsReportService(session).overview(
            start_date=start, end_date=end, limit=limit
        )
    )


@router.get("/trends", response_model=ApiResponse[TrendResponse])
async def trends(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
) -> ApiResponse[TrendResponse]:
    start, end = _resolve_window(start_date, end_date)
    return success(
        await AnalyticsReportService(session).trends(start_date=start, end_date=end)
    )


@router.get("/tool-rankings", response_model=ApiResponse[list[ToolRankingItem]])
async def tool_rankings(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[ToolRankingItem]]:
    start, end = _resolve_window(start_date, end_date)
    return success(
        await AnalyticsReportService(session).tool_rankings(
            start_date=start, end_date=end, limit=limit
        )
    )


@router.get("/funnel-summary", response_model=ApiResponse[list[FunnelSummaryItem]])
async def funnel_summary(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
) -> ApiResponse[list[FunnelSummaryItem]]:
    start, end = _resolve_window(start_date, end_date)
    return success(
        await AnalyticsReportService(session).funnel_summary(
            start_date=start, end_date=end
        )
    )
