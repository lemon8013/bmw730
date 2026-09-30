"""app.admin.departments — HTTP endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.admin.departments.schema import (
    CreateDepartmentRequest,
    DepartmentResponse,
    DepartmentTreeNode,
    UpdateDepartmentRequest,
)
from app.admin.departments.service import DepartmentService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> DepartmentService:
    return DepartmentService(session)


@router.get("/departments/tree", response_model=ApiResponse[list[DepartmentTreeNode]])
async def department_tree(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_VIEW")),
) -> ApiResponse[list[DepartmentTreeNode]]:
    return success(await _service(session).tree(principal))


@router.get("/departments", response_model=ApiResponse[Page[DepartmentResponse]])
async def list_departments(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("DEPARTMENT_VIEW")),
) -> ApiResponse[Page[DepartmentResponse]]:
    return success(
        await _service(session).list_departments(
            principal, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.post("/departments", response_model=ApiResponse[DepartmentResponse])
async def create_department(
    payload: CreateDepartmentRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_CREATE")),
) -> ApiResponse[DepartmentResponse]:
    return success(await _service(session).create_department(principal, payload))


@router.get("/departments/{department_id}", response_model=ApiResponse[DepartmentResponse])
async def get_department(
    department_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_VIEW")),
) -> ApiResponse[DepartmentResponse]:
    return success(await _service(session).get_department(principal, int(department_id)))


@router.put("/departments/{department_id}", response_model=ApiResponse[DepartmentResponse])
async def update_department(
    department_id: str,
    payload: UpdateDepartmentRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_EDIT")),
) -> ApiResponse[DepartmentResponse]:
    return success(
        await _service(session).update_department(principal, int(department_id), payload)
    )


@router.delete("/departments/{department_id}", response_model=ApiResponse[dict])
async def delete_department(
    department_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_DELETE")),
) -> ApiResponse[dict]:
    await _service(session).delete_department(principal, int(department_id))
    return success({"deleted": True, "department_id": department_id})


@router.get(
    "/departments/{department_id}/children",
    response_model=ApiResponse[list[DepartmentResponse]],
)
async def department_children(
    department_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DEPARTMENT_VIEW")),
) -> ApiResponse[list[DepartmentResponse]]:
    return success(await _service(session).children(principal, int(department_id)))


@router.get("/departments/{department_id}/users", response_model=ApiResponse[list[dict]])
async def department_users(
    department_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_VIEW")),
) -> ApiResponse[list[dict[str, Any]]]:
    return success(await _service(session).users_of(principal, int(department_id)))
