"""app.admin.notifications — business logic.

The admin notification layer reuses the platform ``sys_notification`` table. It
can broadcast a system notification (a real insert), mark any notification read
on behalf of an operator, and inspect counts; it does not re-implement the
platform's per-recipient delivery pipeline.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.notifications.repository import AdminNotificationRepository
from app.admin.notifications.schema import (
    CreateNotificationRequest,
    NotificationResponse,
    NotificationTypeStat,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class AdminNotificationService:
    """Administrative notification management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AdminNotificationRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_notifications(
        self,
        *,
        user_type: str | None,
        user_id: int | None,
        notification_type: str | None,
        unread_only: bool,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
        page: PageParams,
    ) -> Page[NotificationResponse]:
        rows, total = await self._repository.list_all(
            user_type=user_type,
            user_id=user_id,
            notification_type=notification_type,
            unread_only=unread_only,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[NotificationResponse.model_validate(row) for row in rows],
            total=total,
            params=page,
        )

    async def send_system_notification(
        self, *, actor_id: int, actor_username: str, payload: CreateNotificationRequest
    ) -> NotificationResponse:
        row = await self._repository.create(
            user_type=payload.user_type,
            user_id=int(payload.user_id),
            notification_type=payload.notification_type,
            title=payload.title,
            content=payload.content,
            payload=payload.payload,
        )
        await self._audit.record(
            self._session,
            action="NOTIFICATION_SEND",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="sys_notification",
            resource_id=row.id,
            after_data={
                "user_type": payload.user_type,
                "user_id": int(payload.user_id),
                "notification_type": payload.notification_type,
            },
        )
        await write_operation_log(
            self._session,
            operation="NOTIFICATION_SEND",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="sys_notification",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return NotificationResponse.model_validate(row)

    async def mark_read(
        self, *, notification_id: int, actor_id: int, actor_username: str
    ) -> NotificationResponse:
        row = await self._repository.get(notification_id)
        if row is None:
            raise NotFoundError("notification not found")
        changed = await self._repository.mark_read_as_admin(
            notification_id, read_at=datetime.datetime.now(datetime.UTC)
        )
        if changed:
            await self._audit.record(
                self._session,
                action="NOTIFICATION_MARK_READ",
                operator_id=int(actor_id),
                operator_username=actor_username,
                resource_type="sys_notification",
                resource_id=row.id,
            )
            await write_operation_log(
                self._session,
                operation="NOTIFICATION_MARK_READ",
                result=RESULT_SUCCESS,
                operator_id=int(actor_id),
                resource_type="sys_notification",
                resource_id=str(int(row.id)),
            )
            await self._session.commit()
        return NotificationResponse.model_validate(row)

    async def stats(
        self, *, start: datetime.datetime | None, end: datetime.datetime | None
    ) -> list[NotificationTypeStat]:
        rows = await self._repository.stats_by_type(start=start, end=end)
        return [
            NotificationTypeStat(
                notification_type=notification_type,
                total=total,
                unread=unread,
            )
            for notification_type, total, unread in rows
        ]
