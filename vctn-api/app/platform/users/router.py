"""app.platform.users — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DbSessionDep
from app.platform.auth.schema import PlatformSessionBrief
from app.platform.auth.service import PlatformAuthService
from app.platform.users.schema import (
    EquipmentRequest,
    EquipmentResponse,
    UpdateProfileRequest,
    UserMeResponse,
)
from app.platform.users.service import PlatformUserService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> PlatformUserService:
    return PlatformUserService(session)


@router.get("/users/me", response_model=ApiResponse[UserMeResponse])
async def me(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[UserMeResponse]:
    return success(await _service(session).me(principal))


@router.put("/users/me", response_model=ApiResponse[UserMeResponse])
async def update_me(
    payload: UpdateProfileRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[UserMeResponse]:
    return success(await _service(session).update_me(principal, payload))


@router.get("/users/me/sessions", response_model=ApiResponse[list[PlatformSessionBrief]])
async def my_sessions(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[list[PlatformSessionBrief]]:
    service = PlatformAuthService(session)
    return success(await service.list_sessions(principal))


@router.post("/users/me/sessions/{session_id}/revoke", response_model=ApiResponse[dict])
async def revoke_my_session(
    session_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[dict]:
    service = PlatformAuthService(session)
    await service.revoke_session(principal, int(session_id))
    return success({"revoked": True, "session_id": session_id})


@router.get("/users/me/equipment", response_model=ApiResponse[EquipmentResponse])
async def my_equipment(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[EquipmentResponse]:
    return success(await _service(session).equipment(principal))


@router.put("/users/me/equipment", response_model=ApiResponse[EquipmentResponse])
async def update_my_equipment(
    payload: EquipmentRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[EquipmentResponse]:
    return success(await _service(session).update_equipment(principal, payload))
