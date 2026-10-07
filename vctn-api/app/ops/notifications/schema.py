"""app.ops.notifications — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class NotificationChannelCreateRequest(ApiModel):
    """Create a notification channel."""

    channel_code: str
    channel_name: str
    channel_type: str = "WEBHOOK"
    config: dict
    enabled: bool = True


class NotificationChannelUpdateRequest(ApiModel):
    """Update a notification channel."""

    channel_name: str | None = None
    channel_type: str | None = None
    config: dict | None = None
    enabled: bool | None = None


class NotificationChannelResponse(ApiModel):
    """A notification channel. Its config never contains a credential."""

    id: StringId
    channel_code: str
    channel_name: str
    channel_type: str
    config: dict
    enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
