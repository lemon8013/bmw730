"""app.platform.users — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class UpdateProfileRequest(ApiModel):
    """Update the signed in business user."""

    nickname: str | None = Field(default=None, max_length=128)
    avatar_url: str | None = Field(default=None, max_length=1024)
    gender: str | None = Field(default=None, max_length=32)
    birthday: datetime.date | None = None
    bio: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=32)
    preferences: dict | None = None


class ProfileResponse(ApiModel):
    """Business user profile."""

    user_id: StringId
    gender: str | None = None
    birthday: datetime.date | None = None
    bio: str | None = None
    timezone: str | None = None
    locale: str | None = None
    preferences: dict | None = None


class UserMeResponse(ApiModel):
    """Signed in business user with its profile."""

    id: StringId
    username: str | None = None
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    status: str
    registered_at: datetime.datetime | None = None
    last_login_at: datetime.datetime | None = None
    profile: ProfileResponse | None = None


class EquipmentSlot(str):
    """Marker type for equipment slot names."""

    pass


class EquipmentRequest(ApiModel):
    """Equip or unequip cosmetics."""

    avatar_cosmetic_id: OptionalStringId = None
    avatar_frame_cosmetic_id: OptionalStringId = None
    crown_cosmetic_id: OptionalStringId = None
    badge_cosmetic_id: OptionalStringId = None
    title_cosmetic_id: OptionalStringId = None
    name_effect_cosmetic_id: OptionalStringId = None


class EquipmentResponse(ApiModel):
    """Currently equipped cosmetics."""

    user_id: StringId
    avatar_cosmetic_id: OptionalStringId = None
    avatar_frame_cosmetic_id: OptionalStringId = None
    crown_cosmetic_id: OptionalStringId = None
    badge_cosmetic_id: OptionalStringId = None
    title_cosmetic_id: OptionalStringId = None
    name_effect_cosmetic_id: OptionalStringId = None
