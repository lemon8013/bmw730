"""app.tools.catalog — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class ToolCategoryResponse(ApiModel):
    """One tool category."""

    id: StringId
    category_code: str
    category_name: str
    description: str | None = None
    icon_url: str | None = None
    sort_order: int
    status: str


class ToolResponse(ApiModel):
    """One tool."""

    id: StringId
    code: str
    name: str
    slug: str
    category_id: OptionalStringId = None
    icon: str | None = None
    summary: str | None = None
    description: str | None = None
    keywords: list[str] = []
    tags: list[str] = []
    component_key: str
    execution_mode: str
    status: str
    sort_order: int
    current_version_id: OptionalStringId = None


class ToolVersionResponse(ApiModel):
    """One tool version."""

    id: StringId
    tool_id: StringId
    version: str
    release_status: str
    changelog: str | None = None
    runtime_config: dict | None = None
    published_at: datetime.datetime | None = None


class ToolAccessResponse(ApiModel):
    """Access decision for one tool and one caller."""

    tool_id: StringId
    subject_type: str
    enabled: bool
    daily_limit: int | None = None
    used_today: int = 0
    remaining: int | None = None
    rate_limit_per_minute: int | None = None
    concurrency_limit: int | None = None


class PopularToolResponse(ApiModel):
    """One entry of the popularity ranking."""

    tool_id: StringId
    tool_name: str | None = None
    tool_slug: str | None = None
    usage_count: int
    unique_user_count: int
    rank_no: int | None = None
    score: float | None = None


class RecentToolResponse(ApiModel):
    """One recently used tool of a caller."""

    tool_id: StringId
    tool_name: str | None = None
    tool_slug: str | None = None
    last_used_at: datetime.datetime
    use_count: int
