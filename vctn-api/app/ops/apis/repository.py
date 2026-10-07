"""app.ops.apis — 数据访问。

端点注册表本身就是只读的：它由访问日志归一化后产出，不由人工 CRUD，所以这里
没有 create/update/soft_delete。Repository 不提交事务，也不决定"没有数据时该
返回什么"，聚合的原始值交回 service 层解释。
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.apis.model import OpsEndpoint
from app.ops.metrics.model import OpsMetricSample


class EndpointRepository:
    """端点与端点指标采样的数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        http_method: str | None = None,
        service_id: int | None = None,
        environment: str | None = None,
        is_monitored: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsEndpoint], int]:
        base = select(OpsEndpoint).where(OpsEndpoint.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsEndpoint.endpoint_key.ilike(f"%{keyword}%")
                | OpsEndpoint.path_pattern.ilike(f"%{keyword}%")
            )
        if http_method:
            base = base.where(OpsEndpoint.http_method == http_method.upper())
        if service_id is not None:
            base = base.where(OpsEndpoint.service_id == service_id)
        if environment:
            base = base.where(OpsEndpoint.environment == environment)
        if is_monitored is not None:
            base = base.where(OpsEndpoint.is_monitored == is_monitored)
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
                    base.order_by(OpsEndpoint.endpoint_key.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, endpoint_id: int) -> OpsEndpoint | None:
        row = await self._session.get(OpsEndpoint, endpoint_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def aggregate_samples(
        self, *, endpoint_id: int, metric_key: str, since: datetime.datetime
    ) -> tuple[float | None, float | None, float | None, int]:
        """按端点 + 指标键聚合一个时间窗口。

        一次查询同时取 sum/avg/max/count：请求数要看累计和，错误率与延迟要看
        均值，P95 序列本身已是分位数、再对分位数求均值没有意义，因此取窗口内
        最大值代表该窗口的 P95。
        """
        result = await self._session.execute(
            select(
                func.sum(OpsMetricSample.value),
                func.avg(OpsMetricSample.value),
                func.max(OpsMetricSample.value),
                func.count(),
            ).where(
                OpsMetricSample.endpoint_id == endpoint_id,
                OpsMetricSample.metric_key == metric_key,
                OpsMetricSample.collected_at >= since,
            )
        )
        row = result.one()
        total = float(row[0]) if row[0] is not None else None
        average = float(row[1]) if row[1] is not None else None
        maximum = float(row[2]) if row[2] is not None else None
        return total, average, maximum, int(row[3] or 0)

    async def count_samples(
        self,
        *,
        endpoint_id: int,
        metric_keys: tuple[str, ...],
        since: datetime.datetime,
    ) -> int:
        """统计窗口内该端点的采样点数量，用于告诉调用方聚合有多少依据。"""
        result = await self._session.execute(
            select(func.count()).where(
                OpsMetricSample.endpoint_id == endpoint_id,
                OpsMetricSample.metric_key.in_(metric_keys),
                OpsMetricSample.collected_at >= since,
            )
        )
        return int(result.scalar_one())
