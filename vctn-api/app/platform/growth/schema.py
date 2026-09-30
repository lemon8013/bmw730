"""app.platform.growth — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class GrowthAccountResponse(ApiModel):
    """Growth account of a business user."""

    user_id: StringId
    total_growth_points: int
    current_level_id: OptionalStringId = None
    current_level_name: str | None = None
    current_level_no: int | None = None
    next_level_id: OptionalStringId = None
    next_level_name: str | None = None
    next_level_points_required: int | None = None
    version: int
    updated_at: datetime.datetime


class GrowthTransactionResponse(ApiModel):
    """One growth ledger entry."""

    id: StringId
    user_id: StringId
    event_id: OptionalStringId = None
    delta_points: int
    balance_after: int
    transaction_type: str
    reason: str | None = None
    created_at: datetime.datetime


class GrowthEventRequest(ApiModel):
    """Internal contract used by outbox consumers and admin adjustments."""

    event_code: str
    growth_points: int
    source_type: str = "SYSTEM"
    source_id: str | None = None
    reason: str | None = None


class GrowthEventResponse(ApiModel):
    """Result of applying one growth event."""

    event_id: StringId
    idempotency_key: str
    user_id: StringId
    event_code: str
    applied_points: int
    total_growth_points: int
    level_changed: bool
    created_duplicate: bool


class GrowthRuleResponse(ApiModel):
    """Growth rule detail."""

    id: StringId
    rule_code: str
    rule_name: str
    event_code: str
    growth_points: int
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool
    conditions: dict | None = None
    description: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
