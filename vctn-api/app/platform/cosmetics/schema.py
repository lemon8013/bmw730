"""app.platform.cosmetics — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import (
    METADATA_COLUMN_ALIAS,
    ApiModel,
    OptionalStringId,
    StringId,
)


class CosmeticResponse(ApiModel):
    """One cosmetic item."""

    id: StringId
    cosmetic_code: str
    cosmetic_name: str
    cosmetic_type: str
    asset_url: str | None = None
    metadata: dict | None = Field(default=None, validation_alias=METADATA_COLUMN_ALIAS)
    status: str
    sort_order: int
    owned: bool = False


class UserCosmeticResponse(ApiModel):
    """A cosmetic owned by a user."""

    id: StringId
    user_id: StringId
    cosmetic_id: StringId
    cosmetic_name: str | None = None
    cosmetic_type: str | None = None
    obtained_at: datetime.datetime
    source_type: str | None = None
    source_id: str | None = None


class EquipmentResponse(ApiModel):
    """Currently equipped cosmetics."""

    user_id: StringId
    avatar_cosmetic_id: OptionalStringId = None
    avatar_frame_cosmetic_id: OptionalStringId = None
    crown_cosmetic_id: OptionalStringId = None
    badge_cosmetic_id: OptionalStringId = None
    title_cosmetic_id: OptionalStringId = None
    name_effect_cosmetic_id: OptionalStringId = None
