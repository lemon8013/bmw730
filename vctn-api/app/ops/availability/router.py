"""app.ops.availability — HTTP 端点。

读端点需要 ``OPS_MONITOR_VIEW``，写端点需要 ``OPS_MONITOR_MANAGE``。探测结果
窗口由调用方通过 ``hours`` 给出，后端不预设观察区间。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.availability.schema import (
    AvailabilityCheckCreateRequest,
    AvailabilityCheckResponse,
    AvailabilityCheckUpdateRequest,
    AvailabilityResultResponse,
)
from app.ops.availability.service import AvailabilityService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AvailabilityService:
    return AvailabilityService(session)


@router.get(
    "/availability",
    response_model=ApiResponse[Page[AvailabilityCheckResponse]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def list_checks(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    check_type: str | None = Query(default=None),
    service_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AvailabilityCheckResponse]]:
    return success(
        await _service(session).list_checks(
            keyword=keyword,
            check_type=check_type,
            service_id=int(service_id) if service_id else None,
            environment=environment,
            enabled=enabled,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post(
    "/availability",
    response_model=ApiResponse[AvailabilityCheckResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_MANAGE"))],
)
async def create_check(
    payload: AvailabilityCheckCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AvailabilityCheckResponse]:
    return success(await _service(session).create_check(principal, payload))


@router.get(
    "/availability/{check_id}",
    response_model=ApiResponse[AvailabilityCheckResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def get_check(
    check_id: str, session: DbSessionDep
) -> ApiResponse[AvailabilityCheckResponse]:
    return success(await _service(session).get_check(int(check_id)))


@router.put(
    "/availability/{check_id}",
    response_model=ApiResponse[AvailabilityCheckResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_MANAGE"))],
)
async def update_check(
    check_id: str,
    payload: AvailabilityCheckUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AvailabilityCheckResponse]:
    return success(
        await _service(session).update_check(principal, int(check_id), payload)
    )


@router.delete(
    "/availability/{check_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_MONITOR_MANAGE"))],
)
async def delete_check(
    check_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_check(principal, int(check_id))
    return success({"deleted": True, "check_id": check_id})


@router.get(
    "/availability/{check_id}/results",
    response_model=ApiResponse[Page[AvailabilityResultResponse]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def list_results(
    check_id: str,
    session: DbSessionDep,
    hours: int = Query(default=24, ge=1, le=720),
    success: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AvailabilityResultResponse]]:
    return success(
        await _service(session).list_results(
            int(check_id),
            hours=hours,
            success=success,
            page=PageParams(page=page, page_size=page_size),
        )
    )
