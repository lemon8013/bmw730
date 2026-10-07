"""app.ops.events — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.events.model import OpsEvent


class EventRepository:
    """Read access for operations events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        event_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsEvent], int]:
        base = select(OpsEvent)
        if event_type:
            base = base.where(OpsEvent.event_type == event_type)
        if severity:
            base = base.where(OpsEvent.severity == severity)
        if source:
            base = base.where(OpsEvent.source == source)
        if start is not None:
            base = base.where(OpsEvent.occurred_at >= start)
        if end is not None:
            base = base.where(OpsEvent.occurred_at <= end)
        if trace_id:
            base = base.where(OpsEvent.trace_id == trace_id)
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
                    base.order_by(OpsEvent.occurred_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, event_id: int) -> OpsEvent | None:
        return await self._session.get(OpsEvent, event_id)
