"""app.admin.auth — HTTP endpoints.

The controller only resolves its inputs, calls the service and renders the
unified envelope. Every rule lives in :mod:`app.admin.auth.service`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.admin.auth.schema import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    PermissionsResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
)
from app.admin.auth.service import AdminAuthService, token_pair_to_response
from app.core.dependencies import DbSessionDep, OptionalRedisDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep, redis: OptionalRedisDep) -> AdminAuthService:
    return AdminAuthService(session, redis=redis)


@router.post("/login", response_model=ApiResponse[LoginResponse], summary="管理员登录")
async def login(
    request: Request,
    payload: LoginRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
) -> ApiResponse[LoginResponse]:
    service = _service(session, redis)
    user, pair, password_expired = await service.login(
        username=payload.username,
        password=payload.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return success(
        LoginResponse(
            token=token_pair_to_response(pair),
            must_change_password=bool(user.must_change_password),
            password_expired=password_expired,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse], summary="刷新令牌")
async def refresh(
    payload: RefreshRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
) -> ApiResponse[TokenResponse]:
    pair = await _service(session, redis).refresh(refresh_token=payload.refresh_token)
    return success(token_pair_to_response(pair))


@router.post("/logout", response_model=ApiResponse[dict], summary="退出登录")
async def logout(
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: AdminPrincipal,
) -> ApiResponse[dict]:
    await _service(session, redis).logout(principal)
    return success({"revoked_session_id": str(principal.session_id)})


@router.get("/me", response_model=ApiResponse[CurrentUserResponse], summary="当前管理员")
async def me(
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: AdminPrincipal,
) -> ApiResponse[CurrentUserResponse]:
    return success(await _service(session, redis).current_user(principal))


@router.get(
    "/permissions",
    response_model=ApiResponse[PermissionsResponse],
    summary="动态权限与菜单",
)
async def permissions(
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: AdminPrincipal,
) -> ApiResponse[PermissionsResponse]:
    return success(await _service(session, redis).permissions(principal))


@router.post("/change-password", response_model=ApiResponse[dict], summary="修改当前管理员密码")
async def change_password(
    payload: ChangePasswordRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: AdminPrincipal,
) -> ApiResponse[dict]:
    await _service(session, redis).change_password(
        principal,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success({"must_change_password": False})


@router.post(
    "/reset-password",
    response_model=ApiResponse[ResetPasswordResponse],
    summary="管理员重置他人密码",
)
async def reset_password(
    payload: ResetPasswordRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: Principal = Depends(require_permission("USER_RESET_PASSWORD")),
) -> ApiResponse[ResetPasswordResponse]:
    service = _service(session, redis)
    return success(
        await service.reset_password(
            principal,
            user_id=int(payload.user_id),
            reason=payload.reason,
        )
    )
