"""app.analytics.reports — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId


class ToolRankingItem(ApiModel):
    """One tool in a usage ranking."""

    tool_id: OptionalStringId | None = None
    execute_count: int
    success_count: int
    failure_count: int
    unique_user_count: int


class OverviewResponse(ApiModel):
    """Top level analytics overview."""

    pv: int
    uv: int
    active_users: int
    tool_top: list[ToolRankingItem]
    generated_at: datetime.datetime


class TrendPoint(ApiModel):
    """One day in a trend series."""

    stat_date: datetime.date
    pv: int
    uv: int


class TrendResponse(ApiModel):
    """A date-bounded trend series."""

    start_date: datetime.date
    end_date: datetime.date
    points: list[TrendPoint]


class FunnelStepSummary(ApiModel):
    """One funnel step with its observed conversion count."""

    step_no: int
    step_code: str
    event_code: str
    enabled: bool
    event_count: int


class FunnelSummaryItem(ApiModel):
    """One funnel and its step-by-step conversion."""

    funnel_code: str
    funnel_name: str
    first_step_count: int
    steps: list[FunnelStepSummary]
