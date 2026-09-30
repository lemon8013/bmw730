"""app.admin.permissions — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.permissions.schema import (
    CreateResourceRequest,
    PermissionResourceResponse,
    PermissionTreeNode,
    UpdateResourceRequest,
)
from app.admin.permissions.service import PermissionService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> PermissionService:
    return PermissionService(session)


@router.get("/permissions/tree", response_model=ApiResponse[list[PermissionTreeNode]])
async def permission_tree(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("PERMISSION_VIEW")),
) -> ApiResponse[list[PermissionTreeNode]]:
    return success(await _service(session).tree())


@router.get(
    "/permissions/resources",
    response_model=ApiResponse[Page[PermissionResourceResponse]],
)
async def list_resources(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("PERMISSION_VIEW")),
) -> ApiResponse[Page[PermissionResourceResponse]]:
    return success(
        await _service(session).list_resources(page=PageParams(page=page, page_size=page_size))
    )


@router.post(
    "/permissions/resources",
    response_model=ApiResponse[PermissionResourceResponse],
)
async def create_resource(
    payload: CreateResourceRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("PERMISSION_RESOURCE_EDIT")),
) -> ApiResponse[PermissionResourceResponse]:
    return success(await _service(session).create_resource(principal, payload))


@router.put(
    "/permissions/resources/{resource_id}",
    response_model=ApiResponse[PermissionResourceResponse],
)
async def update_resource(
    resource_id: str,
    payload: UpdateResourceRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("PERMISSION_RESOURCE_EDIT")),
) -> ApiResponse[PermissionResourceResponse]:
    return success(await _service(session).update_resource(principal, int(resource_id), payload))


@router.delete("/permissions/resources/{resource_id}", response_model=ApiResponse[dict])
async def delete_resource(
    resource_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("PERMISSION_RESOURCE_EDIT")),
) -> ApiResponse[dict]:
    await _service(session).delete_resource(principal, int(resource_id))
    return success({"deleted": True, "resource_id": resource_id})
