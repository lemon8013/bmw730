"""app.ops.dashboard — HTTP endpoints.

Read endpoints require ``OPS_DASHBOARD_VIEW``; every write requires
``OPS_DASHBOARD_MANAGE``. The permission is enforced by the backend
``AuthorizationService`` — the frontend hides the buttons, the backend decides.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.dashboard.schema import (
    DEFAULT_AVAILABILITY_WINDOW_HOURS,
    DEFAULT_RECENT_EVENT_LIMIT,
    MAX_AVAILABILITY_WINDOW_HOURS,
    MAX_RECENT_EVENT_LIMIT,
    DashboardCreateRequest,
    DashboardDetailResponse,
    DashboardResponse,
    DashboardUpdateRequest,
    OverviewResponse,
    WidgetCreateRequest,
    WidgetResponse,
    WidgetUpdateRequest,
)
from app.ops.dashboard.service import DashboardService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> DashboardService:
    return DashboardService(session)


@router.get(
    "/overview",
    response_model=ApiResponse[OverviewResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_VIEW"))],
)
async def get_overview(
    session: DbSessionDep,
    availability_hours: int = Query(
        default=DEFAULT_AVAILABILITY_WINDOW_HOURS, ge=1, le=MAX_AVAILABILITY_WINDOW_HOURS
    ),
    recent_event_limit: int = Query(
        default=DEFAULT_RECENT_EVENT_LIMIT, ge=1, le=MAX_RECENT_EVENT_LIMIT
    ),
) -> ApiResponse[OverviewResponse]:
    return success(
        await _service(session).overview(
            availability_hours=availability_hours,
            recent_event_limit=recent_event_limit,
        )
    )


@router.get(
    "/dashboards",
    response_model=ApiResponse[Page[DashboardResponse]],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_VIEW"))],
)
async def list_dashboards(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[DashboardResponse]]:
    return success(
        await _service(session).list_dashboards(
            keyword=keyword, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.get(
    "/dashboards/{dashboard_id}",
    response_model=ApiResponse[DashboardDetailResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_VIEW"))],
)
async def get_dashboard(
    dashboard_id: str, session: DbSessionDep
) -> ApiResponse[DashboardDetailResponse]:
    return success(await _service(session).get_dashboard(int(dashboard_id)))


@router.post(
    "/dashboards",
    response_model=ApiResponse[DashboardDetailResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def create_dashboard(
    payload: DashboardCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[DashboardDetailResponse]:
    return success(await _service(session).create_dashboard(principal, payload))


@router.put(
    "/dashboards/{dashboard_id}",
    response_model=ApiResponse[DashboardDetailResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def update_dashboard(
    dashboard_id: str,
    payload: DashboardUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[DashboardDetailResponse]:
    return success(
        await _service(session).update_dashboard(principal, int(dashboard_id), payload)
    )


@router.delete(
    "/dashboards/{dashboard_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def delete_dashboard(
    dashboard_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_dashboard(principal, int(dashboard_id))
    return success({"deleted": True, "dashboard_id": dashboard_id})


@router.get(
    "/dashboards/{dashboard_id}/widgets",
    response_model=ApiResponse[list[WidgetResponse]],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_VIEW"))],
)
async def list_widgets(
    dashboard_id: str, session: DbSessionDep
) -> ApiResponse[list[WidgetResponse]]:
    return success(await _service(session).list_widgets(int(dashboard_id)))


@router.post(
    "/dashboards/{dashboard_id}/widgets",
    response_model=ApiResponse[WidgetResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def create_widget(
    dashboard_id: str,
    payload: WidgetCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[WidgetResponse]:
    return success(
        await _service(session).create_widget(principal, int(dashboard_id), payload)
    )


@router.put(
    "/dashboards/{dashboard_id}/widgets/{widget_id}",
    response_model=ApiResponse[WidgetResponse],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def update_widget(
    dashboard_id: str,
    widget_id: str,
    payload: WidgetUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[WidgetResponse]:
    return success(
        await _service(session).update_widget(
            principal, int(dashboard_id), int(widget_id), payload
        )
    )


@router.delete(
    "/dashboards/{dashboard_id}/widgets/{widget_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_DASHBOARD_MANAGE"))],
)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[dict]:
    await _service(session).delete_widget(principal, int(dashboard_id), int(widget_id))
    return success({"deleted": True, "widget_id": widget_id})
