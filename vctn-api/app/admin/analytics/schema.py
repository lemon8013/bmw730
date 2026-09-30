"""app.admin.analytics — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class AnalyticsOverviewResponse(ApiModel):
    """Rollup of every daily analytics stream over a window."""

    start: str
    end: str
    event_total: int
    event_unique_users: int
    event_unique_anonymous: int
    tool_views: int
    tool_starts: int
    tool_executions: int
    tool_success: int
    tool_failure: int
    tool_unique_users: int
    active_user_days: int
    user_event_total: int
    page_views: int


class ToolUsageResponse(ApiModel):
    """Tool usage aggregated over a window."""

    tool_id: OptionalStringId = None
    tool_name: str | None = None
    tool_slug: str | None = None
    view_count: int
    start_count: int
    execute_count: int
    success_count: int
    failure_count: int
    unique_user_count: int


class EventDailyResponse(ApiModel):
    """One daily event rollup row."""

    id: StringId
    stat_date: datetime.date
    event_code: str
    total_count: int
    unique_user_count: int
    unique_anonymous_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class RecomputeResponse(ApiModel):
    """Result of a recompute run."""

    start: str
    end: str
    recomputed_rows: int
