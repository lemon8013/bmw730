"""app.admin.notifications — data access.

Reuses the platform ``sys_notification`` table. The admin layer only inspects
and operates on existing notifications; it does not re-implement the platform
notification delivery pipeline.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.notifications.model import SysNotification
from app.shared.ids import new_id


class AdminNotificationRepository:
    """Data access for administrative notification management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysNotification:
        row = SysNotification(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, notification_id: int) -> SysNotification | None:
        return await self._session.get(SysNotification, notification_id)

    async def list_all(
        self,
        *,
        user_type: str | None,
        user_id: int | None,
        notification_type: str | None,
        unread_only: bool,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysNotification], int]:
        conditions: list[object] = []
        if user_type:
            conditions.append(SysNotification.user_type == user_type)
        if user_id is not None:
            conditions.append(SysNotification.user_id == user_id)
        if notification_type:
            conditions.append(SysNotification.notification_type == notification_type)
        if unread_only:
            conditions.append(SysNotification.read_at.is_(None))
        if start is not None:
            conditions.append(SysNotification.created_at >= start)
        if end is not None:
            conditions.append(SysNotification.created_at <= end)
        total = int(
            (
                await self._session.execute(
                    select(func.count(SysNotification.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(SysNotification)
                    .where(*conditions)
                    .order_by(SysNotification.created_at.desc(), SysNotification.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def mark_read_as_admin(
        self, notification_id: int, *, read_at: datetime.datetime
    ) -> bool:
        result = await self._session.execute(
            update(SysNotification)
            .where(SysNotification.id == notification_id, SysNotification.read_at.is_(None))
            .values(read_at=read_at)
        )
        return int(result.rowcount or 0) > 0

    async def stats_by_type(
        self, *, start: datetime.datetime | None, end: datetime.datetime | None
    ) -> list[tuple[str, int, int]]:
        conditions: list[object] = []
        if start is not None:
            conditions.append(SysNotification.created_at >= start)
        if end is not None:
            conditions.append(SysNotification.created_at <= end)
        rows = (
            (
                await self._session.execute(
                    select(
                        SysNotification.notification_type,
                        func.count(SysNotification.id),
                        func.count(SysNotification.id).filter(SysNotification.read_at.is_(None)),
                    )
                    .where(*conditions)
                    .group_by(SysNotification.notification_type)
                    .order_by(func.count(SysNotification.id).desc())
                )
            )
            .all()
        )
        return [(row[0], int(row[1] or 0), int(row[2] or 0)) for row in rows]
