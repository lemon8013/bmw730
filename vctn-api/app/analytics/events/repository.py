"""app.analytics.events — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events.model import BehaviorEvent, BehaviorIdentityMerge
from app.shared.ids import new_id


class BehaviorEventRepository:
    """Data access for raw tracking events and identity merges."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def event_by_event_id(self, event_id: str) -> BehaviorEvent | None:
        result = await self._session.execute(
            select(BehaviorEvent).where(BehaviorEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def add_event(self, **fields: object) -> BehaviorEvent:
        row = BehaviorEvent(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def count_events(
        self,
        *,
        event_code: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> int:
        stmt = select(func.count(BehaviorEvent.id))
        if event_code is not None:
            stmt = stmt.where(BehaviorEvent.event_code == event_code)
        if start is not None:
            stmt = stmt.where(BehaviorEvent.occurred_at >= start)
        if end is not None:
            stmt = stmt.where(BehaviorEvent.occurred_at < end)
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_events(
        self,
        *,
        event_code: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        limit: int,
        offset: int,
    ) -> list[BehaviorEvent]:
        stmt = select(BehaviorEvent)
        if event_code is not None:
            stmt = stmt.where(BehaviorEvent.event_code == event_code)
        if start is not None:
            stmt = stmt.where(BehaviorEvent.occurred_at >= start)
        if end is not None:
            stmt = stmt.where(BehaviorEvent.occurred_at < end)
        stmt = stmt.order_by(BehaviorEvent.occurred_at.desc(), BehaviorEvent.id.desc())
        stmt = stmt.limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars())

    async def merge_by_key(
        self, *, anonymous_id_hash: str, user_id: int | None
    ) -> BehaviorIdentityMerge | None:
        result = await self._session.execute(
            select(BehaviorIdentityMerge).where(
                BehaviorIdentityMerge.anonymous_id_hash == anonymous_id_hash,
                BehaviorIdentityMerge.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_merge(self, **fields: object) -> BehaviorIdentityMerge:
        row = BehaviorIdentityMerge(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def count_merges(
        self,
        *,
        anonymous_id_hash: str | None = None,
        user_id: int | None = None,
    ) -> int:
        stmt = select(func.count(BehaviorIdentityMerge.id))
        if anonymous_id_hash is not None:
            stmt = stmt.where(BehaviorIdentityMerge.anonymous_id_hash == anonymous_id_hash)
        if user_id is not None:
            stmt = stmt.where(BehaviorIdentityMerge.user_id == user_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_merges(
        self,
        *,
        anonymous_id_hash: str | None = None,
        user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> list[BehaviorIdentityMerge]:
        stmt = select(BehaviorIdentityMerge)
        if anonymous_id_hash is not None:
            stmt = stmt.where(BehaviorIdentityMerge.anonymous_id_hash == anonymous_id_hash)
        if user_id is not None:
            stmt = stmt.where(BehaviorIdentityMerge.user_id == user_id)
        stmt = stmt.order_by(
            BehaviorIdentityMerge.merged_at.desc(), BehaviorIdentityMerge.id.desc()
        )
        stmt = stmt.limit(limit).offset(offset)
        return list((await self._session.execute(stmt)).scalars())
