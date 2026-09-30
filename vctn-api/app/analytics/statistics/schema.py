"""app.analytics.statistics — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class EventDailyResponse(ApiModel):
    """Per-day, per-event-code rollup."""

    id: StringId
    stat_date: datetime.date
    event_code: str
    total_count: int
    unique_user_count: int
    unique_anonymous_count: int
    updated_at: datetime.datetime | None = None


class UserDailyResponse(ApiModel):
    """Per-day, per-visitor activity rollup."""

    id: StringId
    stat_date: datetime.date
    user_id: OptionalStringId | None = None
    anonymous_id_hash: str | None = None
    event_count: int
    active: bool
    first_event_at: datetime.datetime | None = None
    last_event_at: datetime.datetime | None = None


class PageDailyResponse(ApiModel):
    """Per-day, per-page view rollup."""

    id: StringId
    stat_date: datetime.date
    page_code: str
    view_count: int
    unique_user_count: int
    unique_anonymous_count: int
    avg_duration_ms: float | None = None


class ToolDailyResponse(ApiModel):
    """Per-day, per-tool usage rollup."""

    id: StringId
    stat_date: datetime.date
    tool_id: OptionalStringId | None = None
    view_count: int
    start_count: int
    execute_count: int
    success_count: int
    failure_count: int
    copy_count: int
    download_count: int
    unique_user_count: int


class SearchDailyResponse(ApiModel):
    """Per-day, per-keyword search rollup."""

    id: StringId
    stat_date: datetime.date
    search_type: str
    keyword_hash: str
    search_count: int
    result_click_count: int


class FunnelResponse(ApiModel):
    """One funnel step definition."""

    id: StringId
    funnel_code: str
    funnel_name: str
    step_no: int
    step_code: str
    event_code: str
    enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class FunnelCreateRequest(ApiModel):
    """Create a funnel step."""

    funnel_code: str
    funnel_name: str
    step_no: int
    step_code: str
    event_code: str
    enabled: bool = True


class FunnelUpdateRequest(ApiModel):
    """Update a funnel step (partial)."""

    funnel_name: str | None = None
    step_no: int | None = None
    step_code: str | None = None
    event_code: str | None = None
    enabled: bool | None = None


class RecomputeRequest(ApiModel):
    """Trigger an aggregation refresh over a date window."""

    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
