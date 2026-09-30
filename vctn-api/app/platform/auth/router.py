"""app.platform.auth — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.core.dependencies import DbSessionDep, OptionalRedisDep
from app.platform.auth.schema import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PlatformUserBrief,
    RefreshRequest,
    RegisterRequest,
    SendVerificationRequest,
    SendVerificationResponse,
    TokenResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.platform.auth.service import PlatformAuthService, to_user_brief, token_response
from app.shared.authorization.dependencies import (
    OptionalPrincipal,
    PlatformPrincipal,
)
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep, redis: OptionalRedisDep) -> PlatformAuthService:
    return PlatformAuthService(session, redis=redis)


@router.post("/auth/register", response_model=ApiResponse[PlatformUserBrief])
async def register(
    request: Request,
    payload: RegisterRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
) -> ApiResponse[PlatformUserBrief]:
    user = await _service(session, redis).register(
        username=payload.username,
        password=payload.password,
        nickname=payload.nickname,
        email=payload.email,
        phone=payload.phone,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return success(to_user_brief(user))


@router.post("/auth/login", response_model=ApiResponse[LoginResponse])
async def login(
    request: Request,
    payload: LoginRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    anonymous_id: str | None = Header(default=None, alias="X-Anonymous-Id"),
) -> ApiResponse[LoginResponse]:
    return success(
        await _service(session, redis).login(
            identity=payload.identity,
            password=payload.password,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            anonymous_id=anonymous_id,
        )
    )


@router.post("/auth/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    payload: RefreshRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
) -> ApiResponse[TokenResponse]:
    pair = await _service(session, redis).refresh(refresh_token=payload.refresh_token)
    return success(token_response(pair))


@router.post("/auth/logout", response_model=ApiResponse[dict])
async def logout(
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: PlatformPrincipal,
) -> ApiResponse[dict]:
    await _service(session, redis).logout(principal)
    return success({"revoked_session_id": str(principal.session_id)})


@router.get("/auth/me", response_model=ApiResponse[PlatformUserBrief])
async def me(
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: PlatformPrincipal,
) -> ApiResponse[PlatformUserBrief]:
    service = _service(session, redis)
    user = await service.current_user(principal.subject_id)
    return success(to_user_brief(user))


@router.post("/auth/change-password", response_model=ApiResponse[dict])
async def change_password(
    payload: ChangePasswordRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: PlatformPrincipal,
) -> ApiResponse[dict]:
    await _service(session, redis).change_password(
        principal,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success({"changed": True})


@router.post(
    "/auth/send-verification",
    response_model=ApiResponse[SendVerificationResponse],
)
async def send_verification(
    request: Request,
    payload: SendVerificationRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: OptionalPrincipal,
) -> ApiResponse[SendVerificationResponse]:
    return success(
        await _service(session, redis).send_verification(
            verification_type=payload.verification_type,
            target=payload.target,
            user_id=None if principal is None else principal.subject_id,
            ip=request.client.host if request.client else None,
        )
    )


@router.post("/auth/verify", response_model=ApiResponse[VerifyResponse])
async def verify(
    payload: VerifyRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: OptionalPrincipal,
) -> ApiResponse[VerifyResponse]:
    return success(
        await _service(session, redis).verify(
            verification_id=int(payload.verification_id),
            code=payload.code,
            user_id=None if principal is None else principal.subject_id,
        )
    )
