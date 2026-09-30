"""app.admin.notifications — request and response DTOs."""

from __future__ import annotations

from app.platform.notifications.schema import (
    CreateNotificationRequest,
    NotificationResponse,
)
from app.shared.response.dto import ApiModel


class NotificationTypeStat(ApiModel):
    """Notification count grouped by type."""

    notification_type: str
    total: int
    unread: int


# Re-export the platform DTOs so the router imports everything from one place.
__all__ = [
    "NotificationResponse",
    "CreateNotificationRequest",
    "NotificationTypeStat",
]
