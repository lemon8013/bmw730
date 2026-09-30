"""app.admin.tools — request and response DTOs."""

from __future__ import annotations

import datetime

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
    "AccessPolicyAdminResponse",
    "AccessPolicyRequest",
]
