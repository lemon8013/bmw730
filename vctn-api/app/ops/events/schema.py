"""app.ops.events — response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class EventResponse(ApiModel):
    """A recorded operations event."""

    id: StringId
    event_id: str
    event_type: str
    source: str
    resource_type: str | None = None
    resource_id: StringId | None = None
    severity: str
    message: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    occurred_at: datetime.datetime
    metadata: dict | None = None
    created_at: datetime.datetime
