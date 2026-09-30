"""app.analytics.reports — data access (reads the rolled-up statistics)."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.statistics.model import (
    BehaviorEventDaily,
    BehaviorFunnel,
    BehaviorPageDaily,
    BehaviorToolDaily,
    BehaviorUserDaily,
)


class AnalyticsReportRepository:
    """Aggregate queries over the ``*_daily`` rollups (no new tables)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview_counts(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> tuple[int, int, int]:
        """Return ``(pv, uv, active_users)`` for the window."""
        pv = int(
            (
                await self._session.execute(
                    select(func.coalesce(func.sum(BehaviorPageDaily.view_count), 0)).where(
                        BehaviorPageDaily.stat_date >= start_date,
                        BehaviorPageDaily.stat_date <= end_date,
                    )
                )
            ).scalar_one()
        )
        user_uv = int(
            (
                await self._session.execute(
                    select(func.count(func.distinct(BehaviorUserDaily.user_id))).where(
                        BehaviorUserDaily.stat_date >= start_date,
                        BehaviorUserDaily.stat_date <= end_date,
                        BehaviorUserDaily.user_id.isnot(None),
                    )
                )
            ).scalar_one()
        )
        anon_uv = int(
            (
                await self._session.execute(
                    select(
                        func.count(func.distinct(BehaviorUserDaily.anonymous_id_hash))
                    ).where(
                        BehaviorUserDaily.stat_date >= start_date,
                        BehaviorUserDaily.stat_date <= end_date,
                        BehaviorUserDaily.anonymous_id_hash.isnot(None),
                    )
                )
            ).scalar_one()
        )
        active_users = int(
            (
                await self._session.execute(
                    select(func.count(func.distinct(BehaviorUserDaily.user_id))).where(
                        BehaviorUserDaily.stat_date >= start_date,
                        BehaviorUserDaily.stat_date <= end_date,
                    )
                )
            ).scalar_one()
        )
        return pv, user_uv + anon_uv, active_users

    async def tool_ranking(
        self, start_date: datetime.date, end_date: datetime.date, limit: int
    ) -> list[dict]:
        rows = (
            await self._session.execute(
                select(
                    BehaviorToolDaily.tool_id,
                    func.coalesce(func.sum(BehaviorToolDaily.execute_count), 0).label(
                        "execute_count"
                    ),
                    func.coalesce(func.sum(BehaviorToolDaily.success_count), 0).label(
                        "success_count"
                    ),
                    func.coalesce(func.sum(BehaviorToolDaily.failure_count), 0).label(
                        "failure_count"
                    ),
                    func.coalesce(func.sum(BehaviorToolDaily.unique_user_count), 0).label(
                        "unique_user_count"
                    ),
                )
                .where(
                    BehaviorToolDaily.stat_date >= start_date,
                    BehaviorToolDaily.stat_date <= end_date,
                )
                .group_by(BehaviorToolDaily.tool_id)
                .order_by(func.sum(BehaviorToolDaily.execute_count).desc())
                .limit(limit)
            )
        ).all()
        return [
            {
                "tool_id": None if row.tool_id is None else int(row.tool_id),
                "execute_count": int(row.execute_count),
                "success_count": int(row.success_count),
                "failure_count": int(row.failure_count),
                "unique_user_count": int(row.unique_user_count),
            }
            for row in rows
        ]

    async def trend_points(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[dict]:
        pv_rows = (
            await self._session.execute(
                select(
                    BehaviorPageDaily.stat_date,
                    func.coalesce(func.sum(BehaviorPageDaily.view_count), 0).label("pv"),
                )
                .where(
                    BehaviorPageDaily.stat_date >= start_date,
                    BehaviorPageDaily.stat_date <= end_date,
                )
                .group_by(BehaviorPageDaily.stat_date)
            )
        ).all()
        uv_rows = (
            await self._session.execute(
                select(
                    BehaviorUserDaily.stat_date,
                    func.count(func.distinct(BehaviorUserDaily.user_id)).label("user_uv"),
                    func.count(
                        func.distinct(BehaviorUserDaily.anonymous_id_hash)
                    ).label("anon_uv"),
                )
                .where(
                    BehaviorUserDaily.stat_date >= start_date,
                    BehaviorUserDaily.stat_date <= end_date,
                )
                .group_by(BehaviorUserDaily.stat_date)
            )
        ).all()

        uv_by_date: dict[datetime.date, int] = {}
        for row in uv_rows:
            uv_by_date[row.stat_date] = int(row.user_uv) + int(row.anon_uv)

        points: list[dict] = []
        for row in pv_rows:
            points.append(
                {
                    "stat_date": row.stat_date,
                    "pv": int(row.pv),
                    "uv": uv_by_date.get(row.stat_date, 0),
                }
            )
        points.sort(key=lambda item: item["stat_date"])
        return points

    async def enabled_funnels(self) -> list[BehaviorFunnel]:
        rows = (
            await self._session.execute(
                select(BehaviorFunnel)
                .where(BehaviorFunnel.enabled.is_(True))
                .order_by(BehaviorFunnel.funnel_code, BehaviorFunnel.step_no)
            )
        ).scalars()
        return list(rows)

    async def funnel_step_count(
        self,
        event_code: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> int:
        return int(
            (
                await self._session.execute(
                    select(
                        func.coalesce(func.sum(BehaviorEventDaily.total_count), 0)
                    ).where(
                        BehaviorEventDaily.event_code == event_code,
                        BehaviorEventDaily.stat_date >= start_date,
                        BehaviorEventDaily.stat_date <= end_date,
                    )
                )
            ).scalar_one()
        )
