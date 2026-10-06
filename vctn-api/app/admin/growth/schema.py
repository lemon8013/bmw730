"""app.admin.growth — request and response DTOs.

The platform growth endpoints are all ``/me``-shaped and resolve identity from
the signed-in **business user**, so an operator (``sys_user``) can never read
them. This module defines the administrator-facing contract that reads the same
data by explicit ``user_id`` instead.
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId

# ---------------------------------------------------------------------------
# Shared subject
# ---------------------------------------------------------------------------


class BizUserBriefResponse(ApiModel):
    """A platform business user, enough to render a picker and a header."""

    user_id: StringId
    username: str | None = None
    nickname: str | None = None
    email: str | None = None
    status: str
    registered_at: datetime.datetime | None = None
    last_login_at: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Growth (per user)
# ---------------------------------------------------------------------------


class GrowthAccountAdminResponse(ApiModel):
    """Growth account plus the level context the account resolves to."""

    user_id: StringId
    username: str | None = None
    nickname: str | None = None
    total_growth_points: int
    current_level_id: OptionalStringId = None
    current_level_name: str | None = None
    current_level_no: int | None = None
    next_level_id: OptionalStringId = None
    next_level_name: str | None = None
    next_level_points_required: int | None = None
    version: int
    updated_at: datetime.datetime


class GrowthTransactionAdminResponse(ApiModel):
    """One growth ledger entry."""

    id: StringId
    user_id: StringId
    event_id: OptionalStringId = None
    delta_points: int
    balance_after: int
    transaction_type: str
    reason: str | None = None
    created_at: datetime.datetime


class GrowthAdjustRequest(ApiModel):
    """Administrative growth adjustment.

    ``idempotency_key`` is optional: without it every call is a new adjustment,
    which is what an operator correcting a balance wants. Supplying one turns a
    double submit into a no-op instead of a second grant.
    """

    delta_points: int = Field(..., description="正数增加、负数扣减，不得为 0")
    reason: str = Field(default="ADMIN_ADJUSTMENT", max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=255)


class GrowthAdjustResponse(ApiModel):
    """Result of an administrative growth adjustment."""

    user_id: StringId
    delta_points: int
    total_growth_points: int
    level_changed: bool
    transaction_id: OptionalStringId = None


# ---------------------------------------------------------------------------
# Growth rules
# ---------------------------------------------------------------------------


class GrowthRuleCreateRequest(ApiModel):
    """Create one growth rule."""

    rule_code: str = Field(min_length=1, max_length=128)
    rule_name: str = Field(min_length=1, max_length=128)
    event_code: str = Field(min_length=1, max_length=128)
    growth_points: int
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool = True
    conditions: dict[str, Any] | None = None
    description: str | None = None


class GrowthRuleUpdateRequest(ApiModel):
    """Partial update of one growth rule. ``rule_code`` stays immutable."""

    rule_name: str | None = Field(default=None, min_length=1, max_length=128)
    growth_points: int | None = None
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool | None = None
    conditions: dict[str, Any] | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Points (per user)
# ---------------------------------------------------------------------------


class PointAccountAdminResponse(ApiModel):
    """Point account of one business user."""

    user_id: StringId
    username: str | None = None
    nickname: str | None = None
    balance: int
    total_earned: int
    total_spent: int
    version: int
    updated_at: datetime.datetime


class PointTransactionAdminResponse(ApiModel):
    """One point ledger entry."""

    id: StringId
    user_id: StringId
    event_id: str | None = None
    delta_points: int
    balance_after: int
    transaction_type: str
    source_type: str | None = None
    source_id: str | None = None
    reason: str | None = None
    created_at: datetime.datetime


class PointAdjustRequest(ApiModel):
    """Administrative point adjustment."""

    delta_points: int = Field(..., description="正数增加、负数扣减，不得为 0")
    reason: str = Field(default="ADMIN_ADJUSTMENT", max_length=255)


class PointAdjustResponse(ApiModel):
    """Result of an administrative point adjustment."""

    user_id: StringId
    delta_points: int
    balance: int
    transaction_id: StringId


# ---------------------------------------------------------------------------
# Point rules
# ---------------------------------------------------------------------------


class PointRuleCreateRequest(ApiModel):
    """Create one point rule."""

    rule_code: str = Field(min_length=1, max_length=128)
    rule_name: str = Field(min_length=1, max_length=128)
    event_code: str = Field(min_length=1, max_length=128)
    points: int
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool = True
    conditions: dict[str, Any] | None = None
    description: str | None = None


class PointRuleUpdateRequest(ApiModel):
    """Partial update of one point rule. ``rule_code`` stays immutable."""

    rule_name: str | None = Field(default=None, min_length=1, max_length=128)
    points: int | None = None
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool | None = None
    conditions: dict[str, Any] | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------


class LevelCreateRequest(ApiModel):
    """Create one level. ``level_code`` is immutable afterwards."""

    level_code: str = Field(min_length=1, max_length=64)
    level_name: str = Field(min_length=1, max_length=128)
    level_no: int = Field(ge=1)
    min_growth_points: int = Field(ge=0)
    max_growth_points: int | None = Field(default=None, ge=0)
    icon_url: str | None = None
    description: str | None = None
    status: str = Field(default="ACTIVE", max_length=16)
    sort_order: int = 0


class LevelUpdateRequest(ApiModel):
    """Partial update of one level."""

    level_name: str | None = Field(default=None, min_length=1, max_length=128)
    level_no: int | None = Field(default=None, ge=1)
    min_growth_points: int | None = Field(default=None, ge=0)
    max_growth_points: int | None = Field(default=None, ge=0)
    icon_url: str | None = None
    description: str | None = None
    status: str | None = Field(default=None, max_length=16)
    sort_order: int | None = None


class UserLevelAdminResponse(ApiModel):
    """Where one user stands in the level ladder, plus their ladder history."""

    user_id: StringId
    username: str | None = None
    nickname: str | None = None
    total_growth_points: int
    current_level_id: OptionalStringId = None
    current_level_name: str | None = None
    current_level_no: int | None = None
    current_level_icon_url: str | None = None
    next_level_id: OptionalStringId = None
    next_level_name: str | None = None
    next_level_points_required: int | None = None
    level_changed_count: int = 0


class LevelHistoryAdminResponse(ApiModel):
    """One level change record with both levels named."""

    id: StringId
    user_id: StringId
    from_level_id: OptionalStringId = None
    from_level_name: str | None = None
    to_level_id: OptionalStringId = None
    to_level_name: str | None = None
    growth_points: int
    reason: str | None = None
    created_at: datetime.datetime


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TaskCreateRequest(ApiModel):
    """Create one task definition."""

    task_code: str = Field(min_length=1, max_length=128)
    task_name: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=32)
    conditions: dict[str, Any] = Field(default_factory=dict)
    reward: dict[str, Any] | None = None
    start_at: datetime.datetime | None = None
    end_at: datetime.datetime | None = None
    repeatable: bool = False
    status: str = Field(default="ACTIVE", max_length=16)


class TaskUpdateRequest(ApiModel):
    """Partial update of one task definition. ``task_code`` stays immutable."""

    task_name: str | None = Field(default=None, min_length=1, max_length=128)
    task_type: str | None = Field(default=None, min_length=1, max_length=32)
    conditions: dict[str, Any] | None = None
    reward: dict[str, Any] | None = None
    start_at: datetime.datetime | None = None
    end_at: datetime.datetime | None = None
    repeatable: bool | None = None
    status: str | None = Field(default=None, max_length=16)


class UserTaskAdminResponse(ApiModel):
    """One user task with its definition merged in for display."""

    id: StringId
    user_id: StringId
    task_id: StringId
    task_code: str | None = None
    task_name: str | None = None
    task_type: str | None = None
    target_count: int | None = None
    current_count: int = 0
    status: str
    completed_at: datetime.datetime | None = None
    reward_claimed: bool = False
    reward: dict[str, Any] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ---------------------------------------------------------------------------
# Achievements & cosmetics (per user)
# ---------------------------------------------------------------------------


class UserAchievementAdminResponse(ApiModel):
    """Every achievement with whether this user unlocked it."""

    achievement_id: StringId
    achievement_code: str
    achievement_name: str
    conditions: dict[str, Any] | None = None
    reward: dict[str, Any] | None = None
    status: str
    unlocked: bool = False
    achieved_at: datetime.datetime | None = None


class UserCosmeticAdminResponse(ApiModel):
    """One cosmetic with whether this user owns it."""

    cosmetic_id: StringId
    cosmetic_code: str
    cosmetic_name: str
    cosmetic_type: str
    asset_url: str | None = None
    sort_order: int = 0
    owned: bool = False
    obtained_at: datetime.datetime | None = None
    source_type: str | None = None


class UserEquipmentAdminResponse(ApiModel):
    """Currently equipped cosmetics, with names resolved for display."""

    user_id: StringId
    avatar_cosmetic_id: OptionalStringId = None
    avatar_cosmetic_name: str | None = None
    avatar_frame_cosmetic_id: OptionalStringId = None
    avatar_frame_cosmetic_name: str | None = None
    crown_cosmetic_id: OptionalStringId = None
    crown_cosmetic_name: str | None = None
    badge_cosmetic_id: OptionalStringId = None
    badge_cosmetic_name: str | None = None
    title_cosmetic_id: OptionalStringId = None
    title_cosmetic_name: str | None = None
    name_effect_cosmetic_id: OptionalStringId = None
    name_effect_cosmetic_name: str | None = None


# ---------------------------------------------------------------------------
# Cross-module summary
# ---------------------------------------------------------------------------


class UserGrowthSummaryAdminResponse(ApiModel):
    """One user's whole gamification footprint in a single round trip."""

    user: BizUserBriefResponse
    growth: GrowthAccountAdminResponse | None = None
    points: PointAccountAdminResponse | None = None
    level: UserLevelAdminResponse | None = None
    task_total: int = 0
    task_completed: int = 0
    task_reward_claimed: int = 0
    achievement_total: int = 0
    achievement_unlocked: int = 0
    cosmetic_total: int = 0
    cosmetic_owned: int = 0


class GrowthOverviewAdminResponse(ApiModel):
    """Platform-wide gamification totals for the console dashboard."""

    biz_user_count: int = 0
    growth_account_count: int = 0
    total_growth_points: int = 0
    point_account_count: int = 0
    total_point_balance: int = 0
    user_task_count: int = 0
    user_task_completed: int = 0
    user_task_reward_claimed: int = 0
    user_achievement_count: int = 0
    growth_rule_count: int = 0
    growth_rule_enabled: int = 0
    point_rule_count: int = 0
    point_rule_enabled: int = 0
    task_count: int = 0
    achievement_count: int = 0
    level_count: int = 0
    cosmetic_count: int = 0


__all__ = [
    "BizUserBriefResponse",
    "GrowthAccountAdminResponse",
    "GrowthAdjustRequest",
    "GrowthAdjustResponse",
    "GrowthOverviewAdminResponse",
    "GrowthRuleCreateRequest",
    "GrowthRuleUpdateRequest",
    "GrowthTransactionAdminResponse",
    "LevelCreateRequest",
    "LevelHistoryAdminResponse",
    "LevelUpdateRequest",
    "PointAccountAdminResponse",
    "PointAdjustRequest",
    "PointAdjustResponse",
    "PointRuleCreateRequest",
    "PointRuleUpdateRequest",
    "PointTransactionAdminResponse",
    "TaskCreateRequest",
    "TaskUpdateRequest",
    "UserAchievementAdminResponse",
    "UserCosmeticAdminResponse",
    "UserEquipmentAdminResponse",
    "UserGrowthSummaryAdminResponse",
    "UserLevelAdminResponse",
    "UserTaskAdminResponse",
]
