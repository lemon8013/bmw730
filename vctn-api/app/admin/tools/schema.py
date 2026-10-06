"""app.admin.tools — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId
from app.tools.access.schema import AccessPolicyRequest


class ToolCreateRequest(ApiModel):
    """Create a tool (administrative)."""

    code: str
    name: str
    slug: str
    component_key: str
    execution_mode: str
    category_id: int | None = None
    icon: str | None = None
    summary: str | None = None
    description: str | None = None
    keywords: list[str] = []
    tags: list[str] = []
    status: str = "DRAFT"
    sort_order: int = 0


class ToolUpdateRequest(ApiModel):
    """Update a tool (administrative)."""

    code: str | None = None
    name: str | None = None
    slug: str | None = None
    component_key: str | None = None
    execution_mode: str | None = None
    category_id: int | None = None
    icon: str | None = None
    summary: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    tags: list[str] | None = None
    status: str | None = None
    sort_order: int | None = None


class ToolStatusRequest(ApiModel):
    """Set the lifecycle status of a tool."""

    status: str


class ToolUsageAdminResponse(ApiModel):
    """How often one tool was used in the requested window.

    ``unique_user_count`` counts distinct signed in users and
    ``unique_guest_count`` distinct anonymous visitors; the two never overlap
    because ``user_id`` is NULL for guests.
    """

    tool_id: StringId
    tool_name: str | None = None
    tool_slug: str | None = None
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    unique_user_count: int = 0
    unique_guest_count: int = 0
    last_used_at: datetime.datetime | None = None


class ToolUsagePointAdminResponse(ApiModel):
    """One day of one tool's usage."""

    stat_date: datetime.date
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class ToolUsageTrendPointAdminResponse(ApiModel):
    """One day of platform wide tool usage, for the report trend line."""

    stat_date: datetime.date
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class ToolUsageOverviewAdminResponse(ApiModel):
    """Platform wide tool usage totals for one window.

    ``success_rate`` is a percentage in ``[0, 100]`` rounded to two decimals;
    it is 0 when the window holds no usage at all.
    """

    start_date: datetime.date
    end_date: datetime.date
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    unique_user_count: int = 0
    unique_guest_count: int = 0
    active_tool_count: int = 0
    last_used_at: datetime.datetime | None = None


class ToolCategoryCreateRequest(ApiModel):
    """Create a tool category (administrative).

    ``category_code`` is unique among live rows (case insensitive, see
    ``uq_tool_category_code``), so a duplicate code is rejected with a conflict
    rather than silently shadowing the existing category.
    """

    category_code: str = Field(min_length=1, max_length=64)
    category_name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    icon_url: str | None = None
    sort_order: int = 0
    status: str = "ACTIVE"


class ToolCategoryUpdateRequest(ApiModel):
    """Update a tool category (administrative).

    ``category_code`` is deliberately absent: it identifies the category across
    seed data and tooling, so renaming it here would break both.
    """

    category_name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    icon_url: str | None = None
    sort_order: int | None = None
    status: str | None = None


class ToolVisibilityResponse(ApiModel):
    """Who may use one tool.

    The frozen ``tool_access_policy`` carries no ``subject_id``, so visibility is
    two levels only. A tool is either open to everyone (PUBLIC) or reserved for
    signed in users (REGISTERED); anything narrower needs a schema thaw.
    """

    tool_id: StringId
    tool_code: str
    tool_name: str
    tool_slug: str
    status: str
    visibility: str
    guest_enabled: bool
    user_enabled: bool
    configured: bool


class ToolVisibilityRequest(ApiModel):
    """Set one tool's visibility level."""

    visibility: str


class AccessPolicyAdminResponse(ApiModel):
    """One tool access policy with the owning tool's name."""

    id: StringId
    tool_id: OptionalStringId = None
    tool_name: str | None = None
    subject_type: str
    enabled: bool
    daily_limit: int | None = None
    rate_limit_per_minute: int | None = None
    concurrency_limit: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


__all__ = [
    "ToolCreateRequest",
    "ToolUpdateRequest",
    "ToolStatusRequest",
    "ToolUsageAdminResponse",
    "ToolUsagePointAdminResponse",
    "ToolUsageTrendPointAdminResponse",
    "ToolUsageOverviewAdminResponse",
    "ToolCategoryCreateRequest",
    "ToolCategoryUpdateRequest",
    "ToolVisibilityResponse",
    "ToolVisibilityRequest",
    "AccessPolicyAdminResponse",
    "AccessPolicyRequest",
]
