"""app.ops.services — HTTP 端点。

读端点需要 ``OPS_SERVICE_VIEW``，写端点需要 ``OPS_SERVICE_MANAGE``。权限由后端
``AuthorizationService`` 判定：前端只是隐藏按钮，后端才是决定者。
路由内部路径不带 ``/ops`` 前缀，前缀由主程序挂载时统一添加。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.services.schema import (
    ServiceCreateRequest,
    ServiceDependencyCreateRequest,
    ServiceDependencyResponse,
    ServiceResponse,
    ServiceUpdateRequest,
)
from app.ops.services.service import ServiceService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> ServiceService:
    return ServiceService(session)


@router.get(
    "/services",
    response_model=ApiResponse[Page[ServiceResponse]],
    dependencies=[Depends(require_permission("OPS_SERVICE_VIEW"))],
)
async def list_services(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    service_type: str | None = Query(default=None),
    host_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[ServiceResponse]]:
    return success(
        await _service(session).list_services(
            keyword=keyword,
            status=status,
            environment=environment,
            service_type=service_type,
            host_id=int(host_id) if host_id else None,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/services/{service_id}",
    response_model=ApiResponse[ServiceResponse],
    dependencies=[Depends(require_permission("OPS_SERVICE_VIEW"))],
)
async def get_service(
    service_id: str, session: DbSessionDep
) -> ApiResponse[ServiceResponse]:
    return success(await _service(session).get_service(int(service_id)))


@router.post(
    "/services",
    response_model=ApiResponse[ServiceResponse],
    dependencies=[Depends(require_permission("OPS_SERVICE_MANAGE"))],
)
async def create_service(
    payload: ServiceCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[ServiceResponse]:
    return success(await _service(session).create_service(principal, payload))


@router.put(
    "/services/{service_id}",
    response_model=ApiResponse[ServiceResponse],
    dependencies=[Depends(require_permission("OPS_SERVICE_MANAGE"))],
)
async def update_service(
    service_id: str,
    payload: ServiceUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[ServiceResponse]:
    return success(await _service(session).update_service(principal, int(service_id), payload))


@router.delete(
    "/services/{service_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_SERVICE_MANAGE"))],
)
async def delete_service(
    service_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_service(principal, int(service_id))
    return success({"deleted": True, "service_id": service_id})


@router.get(
    "/services/{service_id}/dependencies",
    response_model=ApiResponse[Page[ServiceDependencyResponse]],
    dependencies=[Depends(require_permission("OPS_SERVICE_VIEW"))],
)
async def list_dependencies(
    service_id: str,
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[ServiceDependencyResponse]]:
    return success(
        await _service(session).list_dependencies(
            int(service_id), page=PageParams(page=page, page_size=page_size)
        )
    )


@router.post(
    "/services/{service_id}/dependencies",
    response_model=ApiResponse[ServiceDependencyResponse],
    dependencies=[Depends(require_permission("OPS_SERVICE_MANAGE"))],
)
async def add_dependency(
    service_id: str,
    payload: ServiceDependencyCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[ServiceDependencyResponse]:
    return success(
        await _service(session).add_dependency(principal, int(service_id), payload)
    )


@router.delete(
    "/services/{service_id}/dependencies/{dependency_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_SERVICE_MANAGE"))],
)
async def remove_dependency(
    service_id: str,
    dependency_id: str,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[dict]:
    await _service(session).remove_dependency(
        principal, int(service_id), int(dependency_id)
    )
    return success({"deleted": True, "dependency_id": dependency_id})
