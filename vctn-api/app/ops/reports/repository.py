"""app.ops.reports — 数据访问。

报表**不拥有任何表**：它只聚合采集端已经写入的数据，因此没有对应的迁移。
Repository 不提交事务，也不解释"该窗口是否合理"，那是 service 层的策略。

日期分桶统一按 UTC 计算（`timezone('UTC', ...)`）。所有时间列都是
`TIMESTAMPTZ`，若直接交给 `date_trunc`，结果会随数据库会话时区漂移，同一份
数据在不同机器上会落到不同的桶里。
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import Select, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.agents.model import OpsAgent
from app.ops.alerts.model import OpsAlert
from app.ops.availability.model import OpsAvailabilityCheck, OpsAvailabilityResult
from app.ops.hosts.model import OpsHost
from app.ops.services.model import OpsService


#: 一天的起点，按 UTC 计算。见模块 docstring。
def _utc_day(column: Any) -> Any:
    """把 `TIMESTAMPTZ` 列换算成 UTC 日桶起点。"""
    return func.date_trunc("day", func.timezone("UTC", column))


#: 告警级别到数字的映射，用来在 SQL 里取"最严重的一条"。
_SEVERITY_RANK_CASE = case(
    (OpsAlert.severity == "CRITICAL", 4),
    (OpsAlert.severity == "ERROR", 3),
    (OpsAlert.severity == "WARNING", 2),
    (OpsAlert.severity == "INFO", 1),
    else_=0,
)


class ReportRepository:
    """报表聚合查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- 主机 ---------------------------------------------------------

    async def count_hosts_by_status(self) -> dict[str, int]:
        """返回每种主机状态的数量；表为空时返回空字典。"""
        rows = await self._session.execute(
            select(OpsHost.status, func.count())
            .where(OpsHost.deleted_at.is_(None))
            .group_by(OpsHost.status)
        )
        return {str(status): int(count) for status, count in rows.all()}

    # -- 服务 ---------------------------------------------------------

    async def aggregate_services(
        self, *, abnormal_statuses: frozenset[str]
    ) -> tuple[int, int, float]:
        """返回（总数、异常数、可用率均值）。"""
        row = (
            await self._session.execute(
                select(
                    func.count(),
                    func.count(case((OpsService.status.in_(abnormal_statuses), 1))),
                    func.avg(OpsService.availability_rate),
                ).where(OpsService.deleted_at.is_(None))
            )
        ).one()
        total, abnormal, availability = int(row[0]), int(row[1]), row[2]
        return total, abnormal, float(availability or 0.0)

    # -- 告警 ---------------------------------------------------------

    async def aggregate_alerts(
        self, *, since: datetime.datetime, active_statuses: frozenset[str]
    ) -> tuple[int, int, int, dict[str, int], float | None]:
        """返回（触发数、恢复数、活跃数、按级别分布、MTTR 秒）。

        触发数与恢复数按各自的时间列统计：一条跨窗口边界的告警会记在它触
        发的那一天，恢复记在恢复的那一天，两者相减没有意义，报表并列展示。
        """
        severity_rows = (
            await self._session.execute(
                select(OpsAlert.severity, func.count())
                .where(OpsAlert.triggered_at >= since)
                .group_by(OpsAlert.severity)
            )
        ).all()
        by_severity = {str(severity): int(count) for severity, count in severity_rows}

        row = (
            await self._session.execute(
                select(
                    func.count(),
                    func.count(case((OpsAlert.status.in_(active_statuses), 1))),
                ).where(OpsAlert.triggered_at >= since)
            )
        ).one()
        fired, active = int(row[0]), int(row[1])

        resolved = int(
            (
                await self._session.execute(
                    select(func.count()).where(OpsAlert.resolved_at >= since)
                )
            ).scalar_one()
        )

        mttr = (
            await self._session.execute(
                select(
                    func.avg(
                        extract("epoch", OpsAlert.resolved_at - OpsAlert.triggered_at)
                    )
                ).where(OpsAlert.resolved_at.is_not(None), OpsAlert.resolved_at >= since)
            )
        ).scalar_one()
        return fired, resolved, active, by_severity, None if mttr is None else float(mttr)

    async def alert_trend(
        self, *, since: datetime.datetime
    ) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
        """按天统计触发（并按级别细分）与恢复。

        返回 `(fired_by_day, resolved_by_day)`，键是 `YYYY-MM-DD`。分两步查询
        再合并，而不是一次全外连接：触发时间和恢复时间落在不同的列上，SQL
        里很难对齐，Python 里三行就能拼好。<｜hy_place▁holder▁no▁813｜>
        """
        fired: dict[str, dict[str, int]] = {}
        # The bucket is computed in a sub-query on purpose: rendering the very
        # same expression in both the select list and the GROUP BY gives it two
        # separate bind parameters, and PostgreSQL then refuses the grouping
        # because `$1` and `$4` are not the same expression tree.
        fired_source = (
            select(
                _utc_day(OpsAlert.triggered_at).label("bucket"),
                OpsAlert.severity.label("severity"),
            )
            .where(OpsAlert.triggered_at >= since)
            .subquery()
        )
        rows = await self._session.execute(
            select(
                fired_source.c.bucket, fired_source.c.severity, func.count()
            ).group_by(fired_source.c.bucket, fired_source.c.severity)
        )
        for bucket, severity, count in rows.all():
            day = bucket.strftime("%Y-%m-%d")
            slot = fired.setdefault(day, {})
            slot[str(severity)] = slot.get(str(severity), 0) + int(count)

        resolved: dict[str, int] = {}
        resolved_source = (
            select(_utc_day(OpsAlert.resolved_at).label("bucket"))
            .where(OpsAlert.resolved_at.is_not(None), OpsAlert.resolved_at >= since)
            .subquery()
        )
        rows = await self._session.execute(
            select(resolved_source.c.bucket, func.count()).group_by(
                resolved_source.c.bucket
            )
        )
        for bucket, count in rows.all():
            resolved[bucket.strftime("%Y-%m-%d")] = int(count)
        return fired, resolved

    async def alert_ranking(
        self, *, since: datetime.datetime, limit: int
    ) -> list[tuple[str, int | None, str, int, int, int, datetime.datetime | None]]:
        """按告警条数排行，返回 `（资源类型、资源 ID、告警类型、总数、活跃数、
        最严重级别的排名、最后触发时间）`。"""
        base: Select[Any] = (
            select(
                OpsAlert.resource_type,
                OpsAlert.resource_id,
                OpsAlert.alert_type,
                func.count(),
                func.max(_SEVERITY_RANK_CASE),
                func.max(OpsAlert.triggered_at),
            )
            .where(OpsAlert.triggered_at >= since)
            .group_by(
                OpsAlert.resource_type, OpsAlert.resource_id, OpsAlert.alert_type
            )
            .order_by(func.count().desc(), func.max(OpsAlert.triggered_at).desc())
            .limit(limit)
        )
        rows = (await self._session.execute(base)).all()

        # 活跃数不用窗口里的行数，而是"现在还没恢复"的数：排行的意义是该去
        # 修谁，已经恢复的历史告警不该占着榜首。
        keys = [(str(row[0]), row[1], str(row[2])) for row in rows]
        active_counts = await self._count_active_by_key(
            keys=keys, active_statuses=frozenset({"TRIGGERED", "FIRING", "ACKNOWLEDGED"})
        )
        return [
            (
                str(row[0]),
                None if row[1] is None else int(row[1]),
                str(row[2]),
                int(row[3]),
                active_counts.get((str(row[0]), row[1], str(row[2])), 0),
                int(row[4] or 0),
                row[5],
            )
            for row in rows
        ]

    async def _count_active_by_key(
        self,
        *,
        keys: list[tuple[str, int | None, str]],
        active_statuses: frozenset[str],
    ) -> dict[tuple[str, int | None, str], int]:
        if not keys:
            return {}
        rows = await self._session.execute(
            select(
                OpsAlert.resource_type,
                OpsAlert.resource_id,
                OpsAlert.alert_type,
                func.count(),
            )
            .where(OpsAlert.status.in_(active_statuses))
            .group_by(
                OpsAlert.resource_type, OpsAlert.resource_id, OpsAlert.alert_type
            )
        )
        counts = {
            (str(resource_type), resource_id, str(alert_type)): int(count)
            for resource_type, resource_id, alert_type, count in rows.all()
        }
        return {key: counts.get(key, 0) for key in keys}

    # -- 可用性 -------------------------------------------------------

    async def aggregate_availability(self, *, since: datetime.datetime) -> tuple[int, int]:
        """返回（探测总次数、失败次数）。"""
        row = (
            await self._session.execute(
                select(
                    func.count(),
                    func.count(case((OpsAvailabilityResult.success.is_(False), 1))),
                ).where(OpsAvailabilityResult.checked_at >= since)
            )
        ).one()
        return int(row[0]), int(row[1])

    async def availability_rows(self, *, since: datetime.datetime) -> list[tuple[Any, ...]]:
        """按探测点聚合成功率与延迟，成功率最低的排在最前。"""
        rows = await self._session.execute(
            select(
                OpsAvailabilityCheck.id,
                OpsAvailabilityCheck.check_code,
                OpsAvailabilityCheck.name,
                OpsAvailabilityCheck.target,
                func.count(OpsAvailabilityResult.id),
                func.count(case((OpsAvailabilityResult.success.is_(False), 1))),
                func.avg(OpsAvailabilityResult.latency_ms),
                func.max(OpsAvailabilityResult.latency_ms),
            )
            .join(
                OpsAvailabilityResult,
                OpsAvailabilityResult.check_id == OpsAvailabilityCheck.id,
            )
            .where(
                OpsAvailabilityCheck.deleted_at.is_(None),
                OpsAvailabilityResult.checked_at >= since,
            )
            .group_by(
                OpsAvailabilityCheck.id,
                OpsAvailabilityCheck.check_code,
                OpsAvailabilityCheck.name,
                OpsAvailabilityCheck.target,
            )
            .order_by(
                (
                    func.count(case((OpsAvailabilityResult.success.is_(False), 1)))
                    / func.count(OpsAvailabilityResult.id)
                ).desc(),
                OpsAvailabilityCheck.check_code.asc(),
            )
        )
        return list(rows.all())

    # -- Agent --------------------------------------------------------

    async def aggregate_agents(self, *, online_status: str) -> tuple[int, int]:
        """返回（总数、在线数）。"""
        row = (
            await self._session.execute(
                select(
                    func.count(),
                    func.count(case((OpsAgent.status == online_status, 1))),
                ).where(OpsAgent.deleted_at.is_(None))
            )
        ).one()
        return int(row[0]), int(row[1])
