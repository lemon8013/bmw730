"""app.admin.analytics — HTTP endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.admin.analytics.schema import (
    AnalyticsOverviewResponse,
    EventDailyResponse,
    RecomputeResponse,
    ToolUsageResponse,
)
from app.admin.analytics.service import AdminAnalyticsService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _parse(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError("date filters must be ISO 8601 timestamps") from exc


@router.get("/analytics/overview", response_model=ApiResponse[AnalyticsOverviewResponse])
async def analytics_overview(
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    principal: Principal = Depends(require_permission("ANALYTICS_VIEW")),
) -> ApiResponse[AnalyticsOverviewResponse]:
    return success(
        await AdminAnalyticsService(session).overview(_parse(start), _parse(end))
    )


@router.get("/analytics/tool-usage", response_model=ApiResponse[Page[ToolUsageResponse]])
async def analytics_tool_usage(
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("ANALYTICS_VIEW")),
) -> ApiResponse[Page[ToolUsageResponse]]:
    return success(
        await AdminAnalyticsService(session).tool_usage(
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/analytics/events/daily", response_model=ApiResponse[Page[EventDailyResponse]])
async def analytics_events_daily(
    session: DbSessionDep,
    event_code: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("ANALYTICS_VIEW")),
) -> ApiResponse[Page[EventDailyResponse]]:
    return success(
        await AdminAnalyticsService(session).events_daily(
            event_code=event_code,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post("/analytics/recompute", response_model=ApiResponse[RecomputeResponse])
async def analytics_recompute(
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    principal: Principal = Depends(require_permission("ANALYTICS_VIEW")),
) -> ApiResponse[RecomputeResponse]:
    return success(
        await AdminAnalyticsService(session).recompute(
            actor_id=principal.subject_id, start=_parse(start), end=_parse(end)
        )
    )
