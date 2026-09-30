"""app.analytics.statistics — HTTP endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Path, Query

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
from app.analytics.statistics.service import BehaviorStatisticsService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import (
    require_any_permission,
    require_permission,
)
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()

_VIEW = Depends(require_permission("ANALYTICS_VIEW"))
_MANAGE = Depends(require_any_permission("ANALYTICS_VIEW", "ANALYTICS_EXPORT"))


def _service(session: DbSessionDep) -> BehaviorStatisticsService:
    return BehaviorStatisticsService(session)


@router.get("/events/daily", response_model=ApiResponse[Page[EventDailyResponse]])
async def events_daily(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    event_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[EventDailyResponse]]:
    return success(
        await _service(session).event_daily(
            start_date=start_date,
            end_date=end_date,
            event_code=event_code,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/users/daily", response_model=ApiResponse[Page[UserDailyResponse]])
async def users_daily(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[UserDailyResponse]]:
    return success(
        await _service(session).user_daily(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/pages/daily", response_model=ApiResponse[Page[PageDailyResponse]])
async def pages_daily(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    page_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[PageDailyResponse]]:
    return success(
        await _service(session).page_daily(
            start_date=start_date,
            end_date=end_date,
            page_code=page_code,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/tools/daily", response_model=ApiResponse[Page[ToolDailyResponse]])
async def tools_daily(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    tool_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[ToolDailyResponse]]:
    return success(
        await _service(session).tool_daily(
            start_date=start_date,
            end_date=end_date,
            tool_id=tool_id,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/searches/daily", response_model=ApiResponse[Page[SearchDailyResponse]])
async def searches_daily(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    start_date: datetime.date | None = Query(default=None),
    end_date: datetime.date | None = Query(default=None),
    search_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[SearchDailyResponse]]:
    return success(
        await _service(session).search_daily(
            start_date=start_date,
            end_date=end_date,
            search_type=search_type,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/funnels", response_model=ApiResponse[list[FunnelResponse]])
async def list_funnels(
    session: DbSessionDep,
    _principal: Principal = _VIEW,
    enabled_only: bool = Query(default=False),
) -> ApiResponse[list[FunnelResponse]]:
    return success(await _service(session).list_funnels(enabled_only=enabled_only))


@router.post("/funnels", response_model=ApiResponse[FunnelResponse])
async def create_funnel(
    payload: FunnelCreateRequest,
    session: DbSessionDep,
    principal: Principal = _MANAGE,
) -> ApiResponse[FunnelResponse]:
    return success(
        await _service(session).create_funnel(payload, operator_id=principal.subject_id)
    )


@router.put("/funnels/{funnel_id}", response_model=ApiResponse[FunnelResponse])
async def update_funnel(
    payload: FunnelUpdateRequest,
    session: DbSessionDep,
    principal: Principal = _MANAGE,
    funnel_id: int = Path(..., ge=1),
) -> ApiResponse[FunnelResponse]:
    updated = await _service(session).update_funnel(
        funnel_id, payload, operator_id=principal.subject_id
    )
    if updated is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("the funnel step does not exist")
    return success(updated)


@router.delete("/funnels/{funnel_id}", response_model=ApiResponse[bool])
async def delete_funnel(
    session: DbSessionDep,
    principal: Principal = _MANAGE,
    funnel_id: int = Path(..., ge=1),
) -> ApiResponse[bool]:
    removed = await _service(session).delete_funnel(
        funnel_id, operator_id=principal.subject_id
    )
    if not removed:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("the funnel step does not exist")
    return success(True)


@router.post("/recompute", response_model=ApiResponse[dict[str, int]])
async def recompute(
    payload: RecomputeRequest,
    session: DbSessionDep,
    principal: Principal = _MANAGE,
) -> ApiResponse[dict[str, int]]:
    return success(
        await _service(session).recompute(payload, operator_id=principal.subject_id)
    )
