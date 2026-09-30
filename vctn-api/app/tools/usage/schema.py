"""app.tools.usage — response DTOs.

Every BIGINT identifier is exposed as a string (see :data:`StringId`). Decimal
columns are coerced to ``float`` so they serialise without a ``Decimal`` type.
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class ToolUsageEventResponse(ApiModel):
    """One recorded execution of a tool."""

    id: StringId
    tool_id: OptionalStringId = None
    tool_version_id: OptionalStringId = None
    subject_type: str
    user_id: OptionalStringId = None
    anonymous_id_hash: str | None = None
    execution_mode: str
    success: bool
    duration_ms: int | None = None
    source: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    created_at: datetime.datetime


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


class ToolRecentUsageResponse(ApiModel):
    """One recently used tool of a caller."""

    id: StringId
    user_id: OptionalStringId = None
    tool_id: OptionalStringId = None
    last_used_at: datetime.datetime
    use_count: int


class ToolUsageSummary(ApiModel):
    """Aggregate usage of a tool over a window."""

    tool_id: OptionalStringId = None
    period_start: datetime.datetime
    period_end: datetime.datetime
    total_executions: int
    success_count: int
    failure_count: int
    unique_users: int
    avg_duration_ms: float | None = None


class PopularityRefreshRequest(ApiModel):
    """Parameters for a popularity refresh."""

    stat_date: datetime.date
    window_days: int = 7


class PopularityRefreshResponse(ApiModel):
    """Result of a popularity refresh."""

    stat_date: datetime.date
    window_days: int
    refreshed: int
