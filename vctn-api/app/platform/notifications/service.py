"""app.platform.notifications — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.platform.notifications.repository import NotificationRepository
from app.platform.notifications.schema import (
    CreateNotificationRequest,
    NotificationPage,
    NotificationResponse,
)
from app.shared.events.codes import UserType
from app.shared.pagination.params import PageParams


class NotificationService:
    """Notification creation and reading."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = NotificationRepository(session)
        self._settings = settings or get_settings()

    async def list_for(
        self,
        *,
        user_type: str,
        user_id: int,
        unread_only: bool = False,
        page: PageParams,
    ) -> NotificationPage:
        rows, total, unread = await self._repository.list_for(
            user_type=user_type,
            user_id=user_id,
            unread_only=unread_only,
            limit=page.limit,
            offset=page.offset,
        )
        items = [NotificationResponse.model_validate(row) for row in rows]
        return NotificationPage(
            items=items,
            total=total,
            page=page.page,
            page_size=page.page_size,
            unread_count=unread,
        )

    async def get(
        self, *, user_type: str, user_id: int, notification_id: int
    ) -> NotificationResponse:
        row = await self._repository.get(notification_id)
        if row is None or str(row.user_type) != user_type or int(row.user_id) != user_id:
            raise NotFoundError("notification not found")
        return NotificationResponse.model_validate(row)

    async def create(
        self, actor_id: int, payload: CreateNotificationRequest
    ) -> NotificationResponse:
        """Create a notification (administrative send)."""
        row = await self._repository.create(
            user_type=payload.user_type,
            user_id=int(payload.user_id),
            notification_type=payload.notification_type,
            title=payload.title,
            content=payload.content,
            payload=payload.payload,
        )
        await self._session.commit()
        return NotificationResponse.model_validate(row)

    async def mark_read(self, *, user_type: str, user_id: int, notification_id: int) -> bool:
        row = await self._repository.get(notification_id)
        if row is None or str(row.user_type) != user_type or int(row.user_id) != user_id:
            raise NotFoundError("notification not found")
        changed = await self._repository.mark_read(
            notification_id, read_at=datetime.datetime.now(datetime.UTC)
        )
        await self._session.commit()
        return changed

    async def mark_all_read(self, *, user_type: str, user_id: int) -> int:
        changed = await self._repository.mark_all_read(
            user_type=user_type, user_id=user_id, read_at=datetime.datetime.now(datetime.UTC)
        )
        await self._session.commit()
        return changed

    async def notify(
        self,
        *,
        user_type: str,
        user_id: int,
        notification_type: str,
        title: str,
        content: str,
        payload: dict | None = None,
    ) -> NotificationResponse:
        """Internal helper used by other modules through their own service."""
        row = await self._repository.create(
            user_type=user_type,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            payload=payload,
        )
        await self._session.flush()
        return NotificationResponse.model_validate(row)


def user_type_for(is_admin: bool) -> str:
    """Return the notification recipient discriminator of a caller."""
    return UserType.ADMIN if is_admin else UserType.PLATFORM
