"""app.platform.levels — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class LevelResponse(ApiModel):
    """One level definition."""

    id: StringId
    level_code: str
    level_name: str
    level_no: int
    min_growth_points: int
    max_growth_points: int | None = None
    icon_url: str | None = None
    description: str | None = None
    status: str
    sort_order: int


class LevelBenefitResponse(ApiModel):
    """One level benefit."""

    id: StringId
    level_id: StringId
    benefit_type: str
    benefit_code: str
    benefit_value: dict | None = None
    enabled: bool


class MyLevelResponse(ApiModel):
    """The caller's current level, progress and benefits."""

    user_id: StringId
    total_growth_points: int
    current_level: LevelResponse | None = None
    next_level: LevelResponse | None = None
    points_to_next_level: int | None = None
    benefits: list[LevelBenefitResponse] = []


class LevelHistoryResponse(ApiModel):
    """One level change record."""

    id: StringId
    user_id: StringId
    from_level_id: OptionalStringId = None
    to_level_id: OptionalStringId = None
    growth_points: int
    reason: str | None = None
    created_at: datetime.datetime
