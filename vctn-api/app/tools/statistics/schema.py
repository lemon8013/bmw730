"""app.tools.statistics — request and response DTOs.

Every BIGINT identifier is exposed as a string. Decimal columns are coerced to
``float`` for serialisation.
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class ToolUsageDailyResponse(ApiModel):
    """Daily rollup of a tool's usage."""

    id: StringId
    stat_date: datetime.date
    tool_id: OptionalStringId = None
    total_count: int
    success_count: int
    failure_count: int
    guest_count: int
    user_count: int
    unique_user_count: int
    unique_guest_count: int
    avg_duration_ms: float | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ToolPopularityDailyResponse(ApiModel):
    """One entry of a day's popularity ranking."""

    id: StringId
    stat_date: datetime.date
    window_days: int
    tool_id: OptionalStringId = None
    usage_count: int
    unique_user_count: int
    rank_no: int | None = None
    score: float | None = None
    created_at: datetime.datetime


class StatisticsRefreshRequest(ApiModel):
    """Parameters for a popularity refresh."""

    stat_date: datetime.date
    window_days: int = 7


class StatisticsRefreshResponse(ApiModel):
    """Result of a popularity refresh."""

    stat_date: datetime.date
    window_days: int
    refreshed: int
