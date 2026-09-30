"""app.admin.analytics — data access.

The analytics data lives in the ``*_daily`` rollup tables produced by the
analytics pipeline. This repository reads those rollups directly; it does not
re-implement the pipeline. ``recompute`` re-derives ``behavior_event_daily``
from the raw ``behavior_event`` table for a date window.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events.model import BehaviorEvent
from app.analytics.statistics.model import (
    BehaviorEventDaily,
    BehaviorPageDaily,
    BehaviorToolDaily,
    BehaviorUserDaily,
)
from app.shared.ids import new_id
from app.tools.catalog.model import Tool


def _day_window(
    start: datetime.datetime | None, end: datetime.datetime | None
) -> tuple[datetime.datetime, datetime.datetime]:
    """Default to the last 30 days when no window is supplied."""
    if end is None:
        end = datetime.datetime.now(datetime.UTC)
    if start is None:
        start = end - datetime.timedelta(days=30)
    return start, end


class AdminAnalyticsRepository:
    """Data access for administrative analytics inspection."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> dict[str, object]:
        events = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(BehaviorEventDaily.total_count), 0),
                    func.coalesce(func.sum(BehaviorEventDaily.unique_user_count), 0),
                    func.coalesce(func.sum(BehaviorEventDaily.unique_anonymous_count), 0),
                ).where(
                    BehaviorEventDaily.stat_date >= start.date(),
                    BehaviorEventDaily.stat_date <= end.date(),
                )
            )
        ).one()

        tools = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(BehaviorToolDaily.view_count), 0),
                    func.coalesce(func.sum(BehaviorToolDaily.start_count), 0),
                    func.coalesce(func.sum(BehaviorToolDaily.execute_count), 0),
                    func.coalesce(func.sum(BehaviorToolDaily.success_count), 0),
                    func.coalesce(func.sum(BehaviorToolDaily.failure_count), 0),
                    func.coalesce(func.sum(BehaviorToolDaily.unique_user_count), 0),
                ).where(
                    BehaviorToolDaily.stat_date >= start.date(),
                    BehaviorToolDaily.stat_date <= end.date(),
                )
            )
        ).one()

        users = (
            await self._session.execute(
                select(
                    func.coalesce(func.count(BehaviorUserDaily.id), 0),
                    func.coalesce(func.sum(BehaviorUserDaily.event_count), 0),
                ).where(
                    BehaviorUserDaily.stat_date >= start.date(),
                    BehaviorUserDaily.stat_date <= end.date(),
                )
            )
        ).one()

        pages = (
            await self._session.execute(
                select(func.coalesce(func.sum(BehaviorPageDaily.view_count), 0)).where(
                    BehaviorPageDaily.stat_date >= start.date(),
                    BehaviorPageDaily.stat_date <= end.date(),
                )
            )
        ).one()

        return {
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "event_total": int(events[0] or 0),
            "event_unique_users": int(events[1] or 0),
            "event_unique_anonymous": int(events[2] or 0),
            "tool_views": int(tools[0] or 0),
            "tool_starts": int(tools[1] or 0),
            "tool_executions": int(tools[2] or 0),
            "tool_success": int(tools[3] or 0),
            "tool_failure": int(tools[4] or 0),
            "tool_unique_users": int(tools[5] or 0),
            "active_user_days": int(users[0] or 0),
            "user_event_total": int(users[1] or 0),
            "page_views": int(pages[0] or 0),
        }

    async def tool_usage(
        self, start: datetime.datetime, end: datetime.datetime, limit: int, offset: int
    ) -> tuple[list[dict[str, object]], int]:
        window = sa.between(BehaviorToolDaily.stat_date, start.date(), end.date())
        total = int(
            (
                await self._session.execute(
                    select(func.count(func.distinct(BehaviorToolDaily.tool_id))).where(
                        window, BehaviorToolDaily.tool_id.isnot(None)
                    )
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(
                        BehaviorToolDaily.tool_id,
                        Tool.name,
                        Tool.slug,
                        func.sum(BehaviorToolDaily.view_count).label("view_count"),
                        func.sum(BehaviorToolDaily.start_count).label("start_count"),
                        func.sum(BehaviorToolDaily.execute_count).label("execute_count"),
                        func.sum(BehaviorToolDaily.success_count).label("success_count"),
                        func.sum(BehaviorToolDaily.failure_count).label("failure_count"),
                        func.sum(BehaviorToolDaily.unique_user_count).label("unique_user_count"),
                    )
                    .join(Tool, Tool.id == BehaviorToolDaily.tool_id, isouter=True)
                    .where(window, BehaviorToolDaily.tool_id.isnot(None))
                    .group_by(BehaviorToolDaily.tool_id, Tool.name, Tool.slug)
                    .order_by(func.sum(BehaviorToolDaily.execute_count).desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .all()
        )
        items = [
            {
                "tool_id": None if row.tool_id is None else str(int(row.tool_id)),
                "tool_name": row.name,
                "tool_slug": row.slug,
                "view_count": int(row.view_count or 0),
                "start_count": int(row.start_count or 0),
                "execute_count": int(row.execute_count or 0),
                "success_count": int(row.success_count or 0),
                "failure_count": int(row.failure_count or 0),
                "unique_user_count": int(row.unique_user_count or 0),
            }
            for row in rows
        ]
        return items, total

    async def events_daily(
        self,
        *,
        event_code: str | None,
        start: datetime.datetime,
        end: datetime.datetime,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorEventDaily], int]:
        conditions: list[object] = [
            BehaviorEventDaily.stat_date >= start.date(),
            BehaviorEventDaily.stat_date <= end.date(),
        ]
        if event_code:
            conditions.append(BehaviorEventDaily.event_code == event_code)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorEventDaily.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorEventDaily)
                    .where(*conditions)
                    .order_by(BehaviorEventDaily.stat_date.desc(), BehaviorEventDaily.event_code)
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def recompute_events_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        """Re-derive behavior_event_daily from behavior_event for a window.

        The window is expressed in UTC days so it matches the daily rollup keys.
        Existing rows for the window are removed first, then fresh aggregates are
        inserted; both steps share the service transaction.
        """
        day_col = sa.cast(
            sa.func.date_trunc("day", BehaviorEvent.occurred_at), sa.Date
        )
        aggregate = (
            select(
                day_col.label("stat_date"),
                BehaviorEvent.event_code.label("event_code"),
                func.count().label("total_count"),
                func.count(func.distinct(BehaviorEvent.user_id)).label("unique_user_count"),
                func.count(func.distinct(BehaviorEvent.anonymous_id_hash)).label(
                    "unique_anonymous_count"
                ),
            )
            .where(
                sa.cast(sa.func.date_trunc("day", BehaviorEvent.occurred_at), sa.Date)
                >= start.date(),
                sa.cast(sa.func.date_trunc("day", BehaviorEvent.occurred_at), sa.Date)
                <= end.date(),
            )
            .group_by(day_col, BehaviorEvent.event_code)
        )
        existing = (await self._session.execute(aggregate)).all()
        await self._session.execute(
            delete(BehaviorEventDaily).where(
                BehaviorEventDaily.stat_date >= start.date(),
                BehaviorEventDaily.stat_date <= end.date(),
            )
        )
        inserted = 0
        for row in existing:
            self._session.add(
                BehaviorEventDaily(
                    id=new_id(),
                    stat_date=row.stat_date,
                    event_code=row.event_code,
                    total_count=int(row.total_count or 0),
                    unique_user_count=int(row.unique_user_count or 0),
                    unique_anonymous_count=int(row.unique_anonymous_count or 0),
                )
            )
            inserted += 1
        await self._session.flush()
        return inserted
