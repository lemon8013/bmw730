"""app.ops.notifications — data access."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.alerts.model import OpsAlertNotification
from app.ops.notifications.model import OpsNotificationChannel, OpsNotificationGroup


class NotificationRepository:
    """Read access for notification records and channels."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_notifications(
        self,
        *,
        status: str | None = None,
        alert_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAlertNotification], int]:
        base = select(OpsAlertNotification)
        if status:
            base = base.where(OpsAlertNotification.status == status)
        if alert_id is not None:
            base = base.where(OpsAlertNotification.alert_id == alert_id)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(OpsAlertNotification.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_channels(
        self,
        *,
        keyword: str | None = None,
        channel_type: str | None = None,
        enabled: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsNotificationChannel], int]:
        base = select(OpsNotificationChannel).where(
            OpsNotificationChannel.deleted_at.is_(None)
        )
        if keyword:
            base = base.where(
                OpsNotificationChannel.channel_code.ilike(f"%{keyword}%")
                | OpsNotificationChannel.channel_name.ilike(f"%{keyword}%")
            )
        if channel_type:
            base = base.where(OpsNotificationChannel.channel_type == channel_type)
        if enabled is not None:
            base = base.where(OpsNotificationChannel.enabled == enabled)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(OpsNotificationChannel.channel_code.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_groups_by_codes(self, group_codes: Sequence[str]) -> list[OpsNotificationGroup]:
        """Return the enabled groups among ``group_codes``, in code order.

        A group is only a bundle of channel codes, so resolving a policy group
        down to channels has to happen before delivery. Unknown codes simply do
        not come back; the dispatcher records that as a configuration failure.
        """
        codes = [str(code) for code in group_codes if str(code).strip()]
        if not codes:
            return []
        result = await self._session.execute(
            select(OpsNotificationGroup)
            .where(
                OpsNotificationGroup.deleted_at.is_(None),
                OpsNotificationGroup.enabled.is_(True),
                OpsNotificationGroup.group_code.in_(codes),
            )
            .order_by(OpsNotificationGroup.group_code.asc())
        )
        return list(result.scalars().all())

    async def get_channel(self, channel_id: int) -> OpsNotificationChannel | None:
        row = await self._session.get(OpsNotificationChannel, channel_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_channel_by_code(self, channel_code: str) -> OpsNotificationChannel | None:
        result = await self._session.execute(
            select(OpsNotificationChannel).where(
                OpsNotificationChannel.channel_code == channel_code,
                OpsNotificationChannel.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_channel(self, **fields: object) -> OpsNotificationChannel:
        row = OpsNotificationChannel(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_channel(self, row: OpsNotificationChannel, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete_channel(self, row: OpsNotificationChannel) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
