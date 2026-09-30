"""app.platform.users — business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.platform.users.model import BizUser
from app.platform.users.repository import PlatformUserRepository
from app.platform.users.schema import (
    EquipmentRequest,
    EquipmentResponse,
    ProfileResponse,
    UpdateProfileRequest,
    UserMeResponse,
)
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal


class PlatformUserService:
    """Profile and self-service operations of a business user."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = PlatformUserRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def me(self, principal: Principal) -> UserMeResponse:
        """Return the signed in business user and its profile."""
        user = await self._repository.get(principal.subject_id)
        if user is None:
            raise NotFoundError("user not found")
        return UserMeResponse(
            id=str(int(user.id)),
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            phone=user.phone,
            avatar_url=user.avatar_url,
            status=str(user.status),
            registered_at=user.registered_at,
            last_login_at=user.last_login_at,
            profile=await self._profile_response(int(user.id)),
        )

    async def update_me(
        self, principal: Principal, payload: UpdateProfileRequest
    ) -> UserMeResponse:
        """Update the signed in business user and its profile."""
        user = await self._repository.get(principal.subject_id)
        if user is None:
            raise NotFoundError("user not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        user_fields = {
            key: changes.pop(key) for key in ("nickname", "avatar_url") if key in changes
        }
        if user_fields:
            await self._repository.update_user(user, user_fields)
        if changes:
            await self._repository.upsert_profile(int(user.id), changes)

        await self._audit.record(
            self._session,
            action="PLATFORM_PROFILE_UPDATE",
            operator_id=principal.subject_id,
            resource_type="biz_user",
            resource_id=int(user.id),
            after_data=sorted(changes.keys()) + sorted(user_fields.keys()),
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()
        return await self.me(principal)

    async def equipment(self, principal: Principal) -> EquipmentResponse:
        """Return the cosmetics the caller has equipped."""
        from app.platform.cosmetics.service import CosmeticService

        service = CosmeticService(self._session, self._settings)
        row = await service.equipment_row(principal.subject_id)
        return EquipmentResponse(
            user_id=str(principal.subject_id),
            avatar_cosmetic_id=_optional_id(row.avatar_cosmetic_id),
            avatar_frame_cosmetic_id=_optional_id(row.avatar_frame_cosmetic_id),
            crown_cosmetic_id=_optional_id(row.crown_cosmetic_id),
            badge_cosmetic_id=_optional_id(row.badge_cosmetic_id),
            title_cosmetic_id=_optional_id(row.title_cosmetic_id),
            name_effect_cosmetic_id=_optional_id(row.name_effect_cosmetic_id),
        )

    async def update_equipment(
        self, principal: Principal, payload: EquipmentRequest
    ) -> EquipmentResponse:
        """Equip or unequip cosmetics owned by the caller."""
        from app.platform.cosmetics.service import CosmeticService

        service = CosmeticService(self._session, self._settings)
        await service.equip(
            principal,
            avatar_cosmetic_id=_as_int(payload.avatar_cosmetic_id),
            avatar_frame_cosmetic_id=_as_int(payload.avatar_frame_cosmetic_id),
            crown_cosmetic_id=_as_int(payload.crown_cosmetic_id),
            badge_cosmetic_id=_as_int(payload.badge_cosmetic_id),
            title_cosmetic_id=_as_int(payload.title_cosmetic_id),
            name_effect_cosmetic_id=_as_int(payload.name_effect_cosmetic_id),
        )
        return await self.equipment(principal)

    async def _profile_response(self, user_id: int) -> ProfileResponse | None:
        row = await self._repository.get_profile(user_id)
        if row is None:
            return None
        return ProfileResponse(
            user_id=str(int(row.user_id)),
            gender=row.gender,
            birthday=row.birthday,
            bio=row.bio,
            timezone=row.timezone,
            locale=row.locale,
            preferences=row.preferences,
        )


def _optional_id(value: object | None) -> str | None:
    return None if value is None else str(int(value))  # type: ignore[arg-type]


def _as_int(value: str | None) -> int | None:
    return None if value is None else int(value)


def user_is_active(user: BizUser) -> bool:
    """Return whether a business user account can sign in."""
    return str(user.status) == "ACTIVE"
