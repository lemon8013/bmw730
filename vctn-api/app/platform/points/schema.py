"""app.platform.points — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class PointAccountResponse(ApiModel):
    """Point account of a business user."""

    user_id: StringId
    balance: int
    total_earned: int
    total_spent: int
    version: int
    updated_at: datetime.datetime


class PointTransactionResponse(ApiModel):
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


class PointRuleResponse(ApiModel):
    """Point rule detail."""

    id: StringId
    rule_code: str
    rule_name: str
    event_code: str
    points: int
    daily_limit: int | None = None
    cooldown_seconds: int | None = None
    enabled: bool
    conditions: dict | None = None
    description: str | None = None


class PointAdjustRequest(ApiModel):
    """Administrative point adjustment."""

    delta_points: int
    reason: str = "ADMIN_ADJUSTMENT"


class PointAdjustResponse(ApiModel):
    """Result of an administrative adjustment."""

    user_id: StringId
    delta_points: int
    balance: int
    transaction_id: StringId
