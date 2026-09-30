"""app.admin.users — HTTP endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.admin.auth.schema import ResetPasswordRequest, ResetPasswordResponse
from app.admin.auth.service import AdminAuthService
from app.admin.users.schema import (
    AssignRolesRequest,
    BatchForceLogoutRequest,
    CreateUserRequest,
    ForceLogoutRequest,
    ForceLogoutResponse,
    MoveDepartmentRequest,
    OnlineUserResponse,
    RoleBrief,
    UpdateUserRequest,
    UserListQuery,
    UserResponse,
)
from app.admin.users.service import AdminUserService
from app.core.dependencies import DbSessionDep, OptionalRedisDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AdminUserService:
    return AdminUserService(session)


@router.get("/users/online", response_model=ApiResponse[list[OnlineUserResponse]])
async def online_users(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SESSION_VIEW")),
) -> ApiResponse[list[OnlineUserResponse]]:
    return success(await _service(session).online_users(principal))


@router.post(
    "/users/batch-force-logout",
    response_model=ApiResponse[dict],
    summary="批量强制下线",
)
async def batch_force_logout(
    payload: BatchForceLogoutRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SESSION_REVOKE")),
) -> ApiResponse[dict]:
    result = await _service(session).batch_force_logout(
        principal, [int(value) for value in payload.user_ids], reason=payload.reason
    )
    return success(result)


@router.get("/users", response_model=ApiResponse[Page[UserResponse]])
async def list_users(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("USER_VIEW")),
) -> ApiResponse[Page[UserResponse]]:
    query = UserListQuery(keyword=keyword, department_id=department_id, status=status)
    return success(
        await _service(session).list_users(
            principal, query=query, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.post("/users", response_model=ApiResponse[UserResponse])
async def create_user(
    payload: CreateUserRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_CREATE")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).create_user(principal, payload))


@router.get("/users/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_VIEW")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).get_user(principal, int(user_id)))


@router.put("/users/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_EDIT")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).update_user(principal, int(user_id), payload))


@router.delete("/users/{user_id}", response_model=ApiResponse[dict])
async def delete_user(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_DELETE")),
) -> ApiResponse[dict]:
    await _service(session).delete_user(principal, int(user_id))
    return success({"deleted": True, "user_id": user_id})


@router.post("/users/{user_id}/enable", response_model=ApiResponse[UserResponse])
async def enable_user(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_EDIT")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).set_status(principal, int(user_id), active=True))


@router.post("/users/{user_id}/disable", response_model=ApiResponse[UserResponse])
async def disable_user(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_EDIT")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).set_status(principal, int(user_id), active=False))


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ApiResponse[ResetPasswordResponse],
)
async def reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: Principal = Depends(require_permission("USER_RESET_PASSWORD")),
) -> ApiResponse[ResetPasswordResponse]:
    service = AdminAuthService(session, redis=redis)
    return success(
        await service.reset_password(principal, user_id=int(user_id), reason=payload.reason)
    )


@router.get("/users/{user_id}/roles", response_model=ApiResponse[list[RoleBrief]])
async def get_user_roles(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_VIEW")),
) -> ApiResponse[list[RoleBrief]]:
    return success(await _service(session).user_roles(principal, int(user_id)))


@router.put("/users/{user_id}/roles", response_model=ApiResponse[list[RoleBrief]])
async def assign_user_roles(
    user_id: str,
    payload: AssignRolesRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ROLE_ASSIGN")),
) -> ApiResponse[list[RoleBrief]]:
    return success(await _service(session).assign_roles(principal, int(user_id), payload))


@router.put("/users/{user_id}/department", response_model=ApiResponse[UserResponse])
async def move_user_department(
    user_id: str,
    payload: MoveDepartmentRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_EDIT")),
) -> ApiResponse[UserResponse]:
    return success(await _service(session).move_department(principal, int(user_id), payload))


@router.get("/users/{user_id}/sessions", response_model=ApiResponse[list[dict]])
async def get_user_sessions(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SESSION_VIEW")),
) -> ApiResponse[list[dict[str, Any]]]:
    return success(await _service(session).user_sessions(principal, int(user_id)))


@router.post(
    "/users/{user_id}/force-logout",
    response_model=ApiResponse[ForceLogoutResponse],
)
async def force_logout(
    user_id: str,
    payload: ForceLogoutRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SESSION_REVOKE")),
) -> ApiResponse[ForceLogoutResponse]:
    result = await _service(session).force_logout(principal, int(user_id), reason=payload.reason)
    return success(ForceLogoutResponse.model_validate(result))
