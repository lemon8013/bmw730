"""app.platform.notifications — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.pagination.params import Page
from app.shared.response.dto import ApiModel, StringId


class NotificationResponse(ApiModel):
    """One notification."""

    id: StringId
    user_type: str
    user_id: StringId
    notification_type: str
    title: str
    content: str
    payload: dict | None = None
    read_at: datetime.datetime | None = None
    created_at: datetime.datetime


class CreateNotificationRequest(ApiModel):
    """Create and deliver a notification."""

    user_type: str
    user_id: StringId
    notification_type: str
    title: str
    content: str
    payload: dict | None = None


class NotificationPage(Page[NotificationResponse]):
    """Notification list with the unread counter a UI badge needs."""

    unread_count: int = 0
