"""app.ops.maintenance — HTTP 端点。

读端点需要 ``OPS_MONITOR_VIEW``，写端点需要 ``OPS_MAINTENANCE_MANAGE``：维护
窗口会静默告警通知，是高危配置，因此写权限与"查看监控"解耦。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.maintenance.schema import (
    MaintenanceWindowCreateRequest,
    MaintenanceWindowResponse,
    MaintenanceWindowUpdateRequest,
)
from app.ops.maintenance.service import MaintenanceService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> MaintenanceService:
    return MaintenanceService(session)


@router.get(
    "/maintenance",
    response_model=ApiResponse[Page[MaintenanceWindowResponse]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def list_windows(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    scope_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[MaintenanceWindowResponse]]:
    return success(
        await _service(session).list_windows(
            keyword=keyword,
            scope_type=scope_type,
            scope_id=int(scope_id) if scope_id else None,
            enabled=enabled,
            active=active,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post(
    "/maintenance",
    response_model=ApiResponse[MaintenanceWindowResponse],
    dependencies=[Depends(require_permission("OPS_MAINTENANCE_MANAGE"))],
)
async def create_window(
    payload: MaintenanceWindowCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[MaintenanceWindowResponse]:
    return success(await _service(session).create_window(principal, payload))


@router.get(
    "/maintenance/{window_id}",
    response_model=ApiResponse[MaintenanceWindowResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def get_window(
    window_id: str, session: DbSessionDep
) -> ApiResponse[MaintenanceWindowResponse]:
    return success(await _service(session).get_window(int(window_id)))


@router.put(
    "/maintenance/{window_id}",
    response_model=ApiResponse[MaintenanceWindowResponse],
    dependencies=[Depends(require_permission("OPS_MAINTENANCE_MANAGE"))],
)
async def update_window(
    window_id: str,
    payload: MaintenanceWindowUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[MaintenanceWindowResponse]:
    return success(
        await _service(session).update_window(principal, int(window_id), payload)
    )


@router.delete(
    "/maintenance/{window_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_MAINTENANCE_MANAGE"))],
)
async def delete_window(
    window_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_window(principal, int(window_id))
    return success({"deleted": True, "window_id": window_id})
