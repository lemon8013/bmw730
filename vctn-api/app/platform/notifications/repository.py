"""app.platform.notifications — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.notifications.model import SysNotification


class NotificationRepository:
    """Data access for notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysNotification:
        from app.shared.ids import new_id

        row = SysNotification(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, notification_id: int) -> SysNotification | None:
        return await self._session.get(SysNotification, notification_id)

    async def list_for(
        self,
        *,
        user_type: str,
        user_id: int,
        unread_only: bool = False,
        limit: int,
        offset: int,
    ) -> tuple[list[SysNotification], int, int]:
        conditions = [
            SysNotification.user_type == user_type,
            SysNotification.user_id == user_id,
        ]
        if unread_only:
            conditions.append(SysNotification.read_at.is_(None))
        total = int(
            (
                await self._session.execute(
                    select(func.count(SysNotification.id)).where(*conditions)
                )
            ).scalar_one()
        )
        unread = int(
            (
                await self._session.execute(
                    select(func.count(SysNotification.id)).where(
                        SysNotification.user_type == user_type,
                        SysNotification.user_id == user_id,
                        SysNotification.read_at.is_(None),
                    )
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
        return list(rows), total, unread

    async def mark_read(self, notification_id: int, *, read_at: datetime.datetime) -> bool:
        result = await self._session.execute(
            update(SysNotification)
            .where(SysNotification.id == notification_id, SysNotification.read_at.is_(None))
            .values(read_at=read_at)
        )
        return int(result.rowcount or 0) > 0

    async def mark_all_read(
        self, *, user_type: str, user_id: int, read_at: datetime.datetime
    ) -> int:
        result = await self._session.execute(
            update(SysNotification)
            .where(
                SysNotification.user_type == user_type,
                SysNotification.user_id == user_id,
                SysNotification.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        return int(result.rowcount or 0)
