"""app.tools.access — request and response DTOs."""

from __future__ import annotations

from app.shared.response.dto import ApiModel, StringId


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


class AccessPolicyRequest(ApiModel):
    """Upsert the access policy of one subject type."""

    subject_type: str
    enabled: bool = True
    daily_limit: int | None = None
    rate_limit_per_minute: int | None = None
    concurrency_limit: int | None = None
