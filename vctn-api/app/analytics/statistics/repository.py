"""app.analytics.statistics — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, Date, Numeric, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events.model import BehaviorEvent
from app.analytics.statistics.model import (
    BehaviorEventDaily,
    BehaviorFunnel,
    BehaviorPageDaily,
    BehaviorSearchDaily,
    BehaviorToolDaily,
    BehaviorUserDaily,
)
from app.shared.ids import new_id


def _as_date(value: object) -> datetime.date:
    """A truncated day expression may arrive as a ``datetime`` or a ``date``."""
    if isinstance(value, datetime.datetime):
        return value.date()
    assert isinstance(value, datetime.date)
    return value


class BehaviorStatisticsRepository:
    """Data access for the rolled-up behaviour tables and funnel definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Daily list endpoints
    # ------------------------------------------------------------------
    async def list_event_daily(
        self,
        *,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        event_code: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorEventDaily], int]:
        conds = []
        if start_date is not None:
            conds.append(BehaviorEventDaily.stat_date >= start_date)
        if end_date is not None:
            conds.append(BehaviorEventDaily.stat_date <= end_date)
        if event_code is not None:
            conds.append(BehaviorEventDaily.event_code == event_code)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorEventDaily.id)).where(*conds)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorEventDaily)
                    .where(*conds)
                    .order_by(
                        BehaviorEventDaily.stat_date.desc(),
                        BehaviorEventDaily.event_code,
                        BehaviorEventDaily.id,
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_user_daily(
        self,
        *,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorUserDaily], int]:
        conds = []
        if start_date is not None:
            conds.append(BehaviorUserDaily.stat_date >= start_date)
        if end_date is not None:
            conds.append(BehaviorUserDaily.stat_date <= end_date)
        if user_id is not None:
            conds.append(BehaviorUserDaily.user_id == user_id)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorUserDaily.id)).where(*conds)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorUserDaily)
                    .where(*conds)
                    .order_by(
                        BehaviorUserDaily.stat_date.desc(),
                        BehaviorUserDaily.id,
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_page_daily(
        self,
        *,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        page_code: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorPageDaily], int]:
        conds = []
        if start_date is not None:
            conds.append(BehaviorPageDaily.stat_date >= start_date)
        if end_date is not None:
            conds.append(BehaviorPageDaily.stat_date <= end_date)
        if page_code is not None:
            conds.append(BehaviorPageDaily.page_code == page_code)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorPageDaily.id)).where(*conds)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorPageDaily)
                    .where(*conds)
                    .order_by(
                        BehaviorPageDaily.stat_date.desc(),
                        BehaviorPageDaily.page_code,
                        BehaviorPageDaily.id,
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_tool_daily(
        self,
        *,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        tool_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorToolDaily], int]:
        conds = []
        if start_date is not None:
            conds.append(BehaviorToolDaily.stat_date >= start_date)
        if end_date is not None:
            conds.append(BehaviorToolDaily.stat_date <= end_date)
        if tool_id is not None:
            conds.append(BehaviorToolDaily.tool_id == tool_id)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorToolDaily.id)).where(*conds)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorToolDaily)
                    .where(*conds)
                    .order_by(
                        BehaviorToolDaily.stat_date.desc(),
                        BehaviorToolDaily.tool_id,
                        BehaviorToolDaily.id,
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def list_search_daily(
        self,
        *,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        search_type: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[BehaviorSearchDaily], int]:
        conds = []
        if start_date is not None:
            conds.append(BehaviorSearchDaily.stat_date >= start_date)
        if end_date is not None:
            conds.append(BehaviorSearchDaily.stat_date <= end_date)
        if search_type is not None:
            conds.append(BehaviorSearchDaily.search_type == search_type)
        total = int(
            (
                await self._session.execute(
                    select(func.count(BehaviorSearchDaily.id)).where(*conds)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BehaviorSearchDaily)
                    .where(*conds)
                    .order_by(
                        BehaviorSearchDaily.stat_date.desc(),
                        BehaviorSearchDaily.search_type,
                        BehaviorSearchDaily.keyword_hash,
                        BehaviorSearchDaily.id,
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    # ------------------------------------------------------------------
    # Funnel CRUD
    # ------------------------------------------------------------------
    async def list_funnels(
        self, *, enabled_only: bool = False
    ) -> list[BehaviorFunnel]:
        stmt = select(BehaviorFunnel)
        if enabled_only:
            stmt = stmt.where(BehaviorFunnel.enabled.is_(True))
        stmt = stmt.order_by(BehaviorFunnel.funnel_code, BehaviorFunnel.step_no)
        return list((await self._session.execute(stmt)).scalars())

    async def get_funnel(self, funnel_id: int) -> BehaviorFunnel | None:
        return await self._session.get(BehaviorFunnel, funnel_id)

    async def add_funnel(self, **fields: object) -> BehaviorFunnel:
        row = BehaviorFunnel(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_funnel(
        self, funnel_id: int, **fields: object
    ) -> BehaviorFunnel | None:
        row = await self._session.get(BehaviorFunnel, funnel_id)
        if row is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(row, key, value)
        await self._session.flush()
        return row

    async def delete_funnel(self, funnel_id: int) -> bool:
        row = await self._session.get(BehaviorFunnel, funnel_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    # ------------------------------------------------------------------
    # Recompute (real SQL aggregation from behaviour_event)
    # ------------------------------------------------------------------
    async def recompute_event_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        day_expr = func.date_trunc("day", BehaviorEvent.occurred_at).cast(Date)
        await self._session.execute(
            delete(BehaviorEventDaily).where(
                BehaviorEventDaily.stat_date >= start.date(),
                BehaviorEventDaily.stat_date <= (end - datetime.timedelta(seconds=1)).date(),
            )
        )
        rows = (
            await self._session.execute(
                select(
                    day_expr.label("stat_date"),
                    BehaviorEvent.event_code,
                    func.count(BehaviorEvent.id).label("total_count"),
                    func.count(func.distinct(BehaviorEvent.user_id)).label("unique_user_count"),
                    func.count(func.distinct(BehaviorEvent.anonymous_id_hash)).label(
                        "unique_anonymous_count"
                    ),
                )
                .where(BehaviorEvent.occurred_at >= start, BehaviorEvent.occurred_at < end)
                .group_by(day_expr, BehaviorEvent.event_code)
            )
        ).all()
        for row in rows:
            stat_date = _as_date(row.stat_date)
            self._session.add(
                BehaviorEventDaily(
                    id=new_id(),
                    stat_date=stat_date,
                    event_code=row.event_code,
                    total_count=int(row.total_count),
                    unique_user_count=int(row.unique_user_count),
                    unique_anonymous_count=int(row.unique_anonymous_count),
                )
            )
        return len(rows)

    async def recompute_user_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        day_expr = func.date_trunc("day", BehaviorEvent.occurred_at).cast(Date)
        await self._session.execute(
            delete(BehaviorUserDaily).where(
                BehaviorUserDaily.stat_date >= start.date(),
                BehaviorUserDaily.stat_date <= (end - datetime.timedelta(seconds=1)).date(),
            )
        )
        rows = (
            await self._session.execute(
                select(
                    day_expr.label("stat_date"),
                    BehaviorEvent.user_id,
                    BehaviorEvent.anonymous_id_hash,
                    func.count(BehaviorEvent.id).label("event_count"),
                    func.min(BehaviorEvent.occurred_at).label("first_event_at"),
                    func.max(BehaviorEvent.occurred_at).label("last_event_at"),
                )
                .where(BehaviorEvent.occurred_at >= start, BehaviorEvent.occurred_at < end)
                .group_by(day_expr, BehaviorEvent.user_id, BehaviorEvent.anonymous_id_hash)
            )
        ).all()
        for row in rows:
            stat_date = _as_date(row.stat_date)
            self._session.add(
                BehaviorUserDaily(
                    id=new_id(),
                    stat_date=stat_date,
                    user_id=row.user_id,
                    anonymous_id_hash=row.anonymous_id_hash,
                    event_count=int(row.event_count),
                    active=True,
                    first_event_at=row.first_event_at,
                    last_event_at=row.last_event_at,
                )
            )
        return len(rows)

    async def recompute_page_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        day_expr = func.date_trunc("day", BehaviorEvent.occurred_at).cast(Date)
        await self._session.execute(
            delete(BehaviorPageDaily).where(
                BehaviorPageDaily.stat_date >= start.date(),
                BehaviorPageDaily.stat_date <= (end - datetime.timedelta(seconds=1)).date(),
            )
        )
        rows = (
            await self._session.execute(
                select(
                    day_expr.label("stat_date"),
                    BehaviorEvent.page_code,
                    func.count(BehaviorEvent.id).label("view_count"),
                    func.count(func.distinct(BehaviorEvent.user_id)).label("unique_user_count"),
                    func.count(func.distinct(BehaviorEvent.anonymous_id_hash)).label(
                        "unique_anonymous_count"
                    ),
                    func.avg(
                        BehaviorEvent.properties["duration_ms"].cast(Numeric)
                    ).label("avg_duration"),
                )
                .where(
                    BehaviorEvent.occurred_at >= start,
                    BehaviorEvent.occurred_at < end,
                    BehaviorEvent.page_code.isnot(None),
                )
                .group_by(day_expr, BehaviorEvent.page_code)
            )
        ).all()
        for row in rows:
            stat_date = _as_date(row.stat_date)
            self._session.add(
                BehaviorPageDaily(
                    id=new_id(),
                    stat_date=stat_date,
                    page_code=row.page_code,
                    view_count=int(row.view_count),
                    unique_user_count=int(row.unique_user_count),
                    unique_anonymous_count=int(row.unique_anonymous_count),
                    avg_duration_ms=None if row.avg_duration is None else float(row.avg_duration),
                )
            )
        return len(rows)

    async def recompute_tool_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        day_expr = func.date_trunc("day", BehaviorEvent.occurred_at).cast(Date)
        tool_id_expr = BehaviorEvent.properties["tool_id"].cast(BigInteger)
        await self._session.execute(
            delete(BehaviorToolDaily).where(
                BehaviorToolDaily.stat_date >= start.date(),
                BehaviorToolDaily.stat_date <= (end - datetime.timedelta(seconds=1)).date(),
            )
        )
        rows = (
            await self._session.execute(
                select(
                    day_expr.label("stat_date"),
                    tool_id_expr.label("tool_id"),
                    func.count(BehaviorEvent.id).label("view_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_START")
                    .label("start_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_EXECUTE")
                    .label("execute_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_EXECUTE_SUCCESS")
                    .label("success_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_EXECUTE_FAILURE")
                    .label("failure_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_COPY")
                    .label("copy_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "TOOL_DOWNLOAD")
                    .label("download_count"),
                    func.count(func.distinct(BehaviorEvent.user_id)).label("unique_user_count"),
                )
                .where(
                    tool_id_expr.isnot(None),
                    BehaviorEvent.occurred_at >= start,
                    BehaviorEvent.occurred_at < end,
                )
                .group_by(day_expr, tool_id_expr)
            )
        ).all()
        for row in rows:
            stat_date = _as_date(row.stat_date)
            tool_id = None if row.tool_id is None else int(row.tool_id)
            self._session.add(
                BehaviorToolDaily(
                    id=new_id(),
                    stat_date=stat_date,
                    tool_id=tool_id,
                    view_count=int(row.view_count),
                    start_count=int(row.start_count),
                    execute_count=int(row.execute_count),
                    success_count=int(row.success_count),
                    failure_count=int(row.failure_count),
                    copy_count=int(row.copy_count),
                    download_count=int(row.download_count),
                    unique_user_count=int(row.unique_user_count),
                )
            )
        return len(rows)

    async def recompute_search_daily(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> int:
        day_expr = func.date_trunc("day", BehaviorEvent.occurred_at).cast(Date)
        search_type_expr = BehaviorEvent.properties["search_type"].astext
        keyword_hash_expr = BehaviorEvent.properties["keyword_hash"].astext
        await self._session.execute(
            delete(BehaviorSearchDaily).where(
                BehaviorSearchDaily.stat_date >= start.date(),
                BehaviorSearchDaily.stat_date <= (end - datetime.timedelta(seconds=1)).date(),
            )
        )
        rows = (
            await self._session.execute(
                select(
                    day_expr.label("stat_date"),
                    search_type_expr.label("search_type"),
                    keyword_hash_expr.label("keyword_hash"),
                    func.count(BehaviorEvent.id).label("search_count"),
                    func.count(BehaviorEvent.id)
                    .filter(BehaviorEvent.event_code == "SEARCH_CLICK")
                    .label("result_click_count"),
                )
                .where(
                    search_type_expr.isnot(None),
                    keyword_hash_expr.isnot(None),
                    BehaviorEvent.occurred_at >= start,
                    BehaviorEvent.occurred_at < end,
                )
                .group_by(day_expr, search_type_expr, keyword_hash_expr)
            )
        ).all()
        for row in rows:
            stat_date = _as_date(row.stat_date)
            self._session.add(
                BehaviorSearchDaily(
                    id=new_id(),
                    stat_date=stat_date,
                    search_type=row.search_type,
                    keyword_hash=row.keyword_hash,
                    search_count=int(row.search_count),
                    result_click_count=int(row.result_click_count),
                )
            )
        return len(rows)
