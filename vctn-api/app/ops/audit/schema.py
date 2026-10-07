"""app.ops.audit — response DTOs.

This module is the ops readable projection of the audit trail and is
**read-only**: the trail is append-only, so there is no create, update or delete
DTO here by design.
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class AuditRecordResponse(ApiModel):
    """One recorded ops action."""

    id: StringId
    operator_id: StringId | None = None
    operator_username: str | None = None
    action: str
    resource_type: str
    resource_id: StringId | None = None
    result: str
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    before_data: dict | None = None
    after_data: dict | None = None
    created_at: datetime.datetime
