"""app.platform.cosmetics — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DbSessionDep
from app.platform.cosmetics.schema import CosmeticResponse, EquipmentResponse, UserCosmeticResponse
from app.platform.cosmetics.service import CosmeticService
from app.platform.users.schema import EquipmentRequest
from app.shared.authorization.dependencies import OptionalPrincipal, PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> CosmeticService:
    return CosmeticService(session)


@router.get("/cosmetics", response_model=ApiResponse[list[CosmeticResponse]])
async def list_cosmetics(
    session: DbSessionDep,
    principal: OptionalPrincipal,
) -> ApiResponse[list[CosmeticResponse]]:
    user_id = None if principal is None or not principal.is_platform_user else principal.subject_id
    return success(await _service(session).list_cosmetics(user_id))


@router.get("/cosmetics/me", response_model=ApiResponse[list[UserCosmeticResponse]])
async def my_cosmetics(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[list[UserCosmeticResponse]]:
    return success(await _service(session).my_cosmetics(principal.subject_id))


@router.put("/cosmetics/me/equipment", response_model=ApiResponse[EquipmentResponse])
async def equip_cosmetics(
    payload: EquipmentRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[EquipmentResponse]:
    row = await _service(session).equip(
        principal,
        avatar_cosmetic_id=_int_or_none(payload.avatar_cosmetic_id),
        avatar_frame_cosmetic_id=_int_or_none(payload.avatar_frame_cosmetic_id),
        crown_cosmetic_id=_int_or_none(payload.crown_cosmetic_id),
        badge_cosmetic_id=_int_or_none(payload.badge_cosmetic_id),
        title_cosmetic_id=_int_or_none(payload.title_cosmetic_id),
        name_effect_cosmetic_id=_int_or_none(payload.name_effect_cosmetic_id),
    )
    return success(
        EquipmentResponse(
            user_id=str(int(row.user_id)),
            avatar_cosmetic_id=_str_or_none(row.avatar_cosmetic_id),
            avatar_frame_cosmetic_id=_str_or_none(row.avatar_frame_cosmetic_id),
            crown_cosmetic_id=_str_or_none(row.crown_cosmetic_id),
            badge_cosmetic_id=_str_or_none(row.badge_cosmetic_id),
            title_cosmetic_id=_str_or_none(row.title_cosmetic_id),
            name_effect_cosmetic_id=_str_or_none(row.name_effect_cosmetic_id),
        )
    )


def _int_or_none(value: str | None) -> int | None:
    return None if value is None else int(value)


def _str_or_none(value: object | None) -> str | None:
    return None if value is None else str(int(value))  # type: ignore[arg-type]
