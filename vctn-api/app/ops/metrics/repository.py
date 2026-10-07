"""app.ops.metrics — data access.

Repository methods only read or mutate rows; the service owns validation,
auditing and transaction boundaries.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.metrics.model import (
    OpsMetricDaily,
    OpsMetricDefinition,
    OpsMetricHourly,
    OpsMetricSample,
)


@dataclass(frozen=True, slots=True)
class MetricSeriesValue:
    """A normalized raw or rollup point returned to the service."""

    timestamp: datetime.datetime
    value: float
    min_value: float
    max_value: float
    sum_value: float
    sample_count: int


class MetricRepository:
    """Data access for metric definitions, samples and rollups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_definitions(
        self,
        *,
        keyword: str | None = None,
        metric_type: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsMetricDefinition], int]:
        base = select(OpsMetricDefinition).where(OpsMetricDefinition.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsMetricDefinition.metric_key.ilike(f"%{keyword}%")
                | OpsMetricDefinition.metric_name.ilike(f"%{keyword}%")
            )
        if metric_type:
            base = base.where(OpsMetricDefinition.metric_type == metric_type)
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
                    base.order_by(OpsMetricDefinition.metric_key.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_definition_by_key(self, metric_key: str) -> OpsMetricDefinition | None:
        result = await self._session.execute(
            select(OpsMetricDefinition).where(
                OpsMetricDefinition.metric_key == metric_key,
                OpsMetricDefinition.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_definition_keys(self, metric_keys: set[str]) -> set[str]:
        if not metric_keys:
            return set()
        rows = (
            await self._session.execute(
                select(OpsMetricDefinition.metric_key).where(
                    OpsMetricDefinition.metric_key.in_(metric_keys),
                    OpsMetricDefinition.deleted_at.is_(None),
                )
            )
        ).scalars()
        return {str(key) for key in rows}

    async def create_samples(self, rows: list[dict[str, object]]) -> list[OpsMetricSample]:
        samples = [OpsMetricSample(**fields) for fields in rows]  # type: ignore[arg-type]
        self._session.add_all(samples)
        await self._session.flush()
        return samples

    async def list_raw_series(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        host_id: int | None = None,
        service_id: int | None = None,
        endpoint_id: int | None = None,
    ) -> list[MetricSeriesValue]:
        query = select(OpsMetricSample).where(
            OpsMetricSample.metric_key == metric_key,
            OpsMetricSample.collected_at >= start,
            OpsMetricSample.collected_at <= end,
        )
        if host_id is not None:
            query = query.where(OpsMetricSample.host_id == host_id)
        if service_id is not None:
            query = query.where(OpsMetricSample.service_id == service_id)
        if endpoint_id is not None:
            query = query.where(OpsMetricSample.endpoint_id == endpoint_id)
        rows = (
            await self._session.execute(query.order_by(OpsMetricSample.collected_at.asc()))
        ).scalars()
        return [
            MetricSeriesValue(
                timestamp=row.collected_at,
                value=float(row.value),
                min_value=float(row.value),
                max_value=float(row.value),
                sum_value=float(row.value),
                sample_count=1,
            )
            for row in rows
        ]

    async def list_hourly_series(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        dimension_key: str | None = None,
    ) -> list[MetricSeriesValue]:
        return await self._list_rollup_series(
            OpsMetricHourly,
            metric_key=metric_key,
            start=start,
            end=end,
            dimension_key=dimension_key,
        )

    async def list_daily_series(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        dimension_key: str | None = None,
    ) -> list[MetricSeriesValue]:
        return await self._list_rollup_series(
            OpsMetricDaily,
            metric_key=metric_key,
            start=start,
            end=end,
            dimension_key=dimension_key,
        )

    async def _list_rollup_series(
        self,
        model: Any,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        dimension_key: str | None,
    ) -> list[MetricSeriesValue]:
        query = select(
            model.bucket_at,
            func.sum(model.sum_value),
            func.min(model.min_value),
            func.max(model.max_value),
            func.sum(model.sample_count),
        ).where(
            model.metric_key == metric_key,
            model.bucket_at >= start,
            model.bucket_at <= end,
        )
        if dimension_key is not None:
            query = query.where(model.dimension_key == dimension_key)
        query = query.group_by(model.bucket_at).order_by(model.bucket_at.asc())
        rows = (await self._session.execute(query)).all()
        points: list[MetricSeriesValue] = []
        for bucket_at, sum_value, min_value, max_value, sample_count in rows:
            count = int(sample_count or 0)
            total = float(sum_value or 0.0)
            if count <= 0:
                continue
            points.append(
                MetricSeriesValue(
                    timestamp=bucket_at,
                    value=total / count,
                    min_value=float(min_value if min_value is not None else total / count),
                    max_value=float(max_value if max_value is not None else total / count),
                    sum_value=total,
                    sample_count=count,
                )
            )
        return points
