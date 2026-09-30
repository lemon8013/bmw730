"""app.admin.roles — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.roles.schema import (
    AssignParentsRequest,
    AssignPermissionsRequest,
    CreateRoleRequest,
    ParentRoleBrief,
    PermissionBrief,
    RoleResponse,
    UpdateRoleRequest,
)
from app.admin.roles.service import RoleService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> RoleService:
    return RoleService(session)


@router.get("/roles", response_model=ApiResponse[Page[RoleResponse]])
async def list_roles(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("ROLE_VIEW")),
) -> ApiResponse[Page[RoleResponse]]:
    return success(
        await _service(session).list_roles(
            principal, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.post("/roles", response_model=ApiResponse[RoleResponse])
async def create_role(
    payload: CreateRoleRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_CREATE")),
) -> ApiResponse[RoleResponse]:
    return success(await _service(session).create_role(principal, payload))


@router.get("/roles/{role_id}", response_model=ApiResponse[RoleResponse])
async def get_role(
    role_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_VIEW")),
) -> ApiResponse[RoleResponse]:
    return success(await _service(session).get_role(principal, int(role_id)))


@router.put("/roles/{role_id}", response_model=ApiResponse[RoleResponse])
async def update_role(
    role_id: str,
    payload: UpdateRoleRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_EDIT")),
) -> ApiResponse[RoleResponse]:
    return success(await _service(session).update_role(principal, int(role_id), payload))


@router.delete("/roles/{role_id}", response_model=ApiResponse[dict])
async def delete_role(
    role_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_DELETE")),
) -> ApiResponse[dict]:
    await _service(session).delete_role(principal, int(role_id))
    return success({"deleted": True, "role_id": role_id})


@router.get(
    "/roles/{role_id}/permissions",
    response_model=ApiResponse[list[PermissionBrief]],
)
async def get_role_permissions(
    role_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_VIEW")),
) -> ApiResponse[list[PermissionBrief]]:
    return success(await _service(session).role_permissions(principal, int(role_id)))


@router.put(
    "/roles/{role_id}/permissions",
    response_model=ApiResponse[list[PermissionBrief]],
)
async def assign_role_permissions(
    role_id: str,
    payload: AssignPermissionsRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_PERMISSION_EDIT")),
) -> ApiResponse[list[PermissionBrief]]:
    return success(await _service(session).assign_permissions(principal, int(role_id), payload))


@router.get("/roles/{role_id}/parents", response_model=ApiResponse[list[ParentRoleBrief]])
async def get_role_parents(
    role_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_VIEW")),
) -> ApiResponse[list[ParentRoleBrief]]:
    return success(await _service(session).role_parents(principal, int(role_id)))


@router.put("/roles/{role_id}/parents", response_model=ApiResponse[list[ParentRoleBrief]])
async def assign_role_parents(
    role_id: str,
    payload: AssignParentsRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_INHERIT_EDIT")),
) -> ApiResponse[list[ParentRoleBrief]]:
    return success(await _service(session).assign_parents(principal, int(role_id), payload))
