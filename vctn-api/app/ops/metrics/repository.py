"""app.ops.metrics — data access.

Repository methods only read or mutate rows; the service owns validation,
auditing and transaction boundaries.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.metrics.model import (
    OpsMetricDaily,
    OpsMetricDefinition,
    OpsMetricHourly,
    OpsMetricSample,
)
from app.shared.ids import new_id


@dataclass(frozen=True, slots=True)
class MetricSeriesValue:
    """A normalized raw or rollup point returned to the service."""

    timestamp: datetime.datetime
    value: float
    min_value: float
    max_value: float
    sum_value: float
    sample_count: int


#: Hourly rollup of the raw samples. The bucket is computed in a sub-query so
#: that ``date_trunc`` binds exactly once: rendered in both the select list and
#: the ``GROUP BY`` it becomes two different parameters and PostgreSQL rejects
#: the grouping because they are not the same expression tree.
_AGGREGATE_RAW_SQL: Final[str] = """
SELECT metric_key,
       host_id,
       service_id,
       endpoint_id,
       environment,
       bucket_at,
       count(*)          AS sample_count,
       sum(value)        AS sum_value,
       min(value)        AS min_value,
       max(value)        AS max_value
FROM (
    SELECT metric_key,
           host_id,
           service_id,
           endpoint_id,
           environment,
           value,
           date_trunc('hour', collected_at) AS bucket_at
    FROM ops_metric_sample
    WHERE collected_at >= :start AND collected_at < :end
) AS raw
GROUP BY metric_key, host_id, service_id, endpoint_id, environment, bucket_at
"""

#: Daily rollup built from the hourly table - same sub-query reason, and the
#: same reason for not using the raw table: raw samples are purged after seven
#: days while the daily table keeps 180, so yesterday must still be rebuildable.
_AGGREGATE_HOURLY_SQL: Final[str] = """
SELECT metric_key,
       dimension_key,
       bucket_at,
       sum(sample_count) AS sample_count,
       sum(sum_value)    AS sum_value,
       min(min_value)    AS min_value,
       max(max_value)    AS max_value
FROM (
    SELECT metric_key,
           dimension_key,
           sample_count,
           sum_value,
           min_value,
           max_value,
           date_trunc('day', bucket_at) AS bucket_at
    FROM ops_metric_hourly
    WHERE bucket_at >= :start AND bucket_at < :end
) AS hourly
GROUP BY metric_key, dimension_key, bucket_at
"""


def build_dimension_key(
    *,
    environment: str,
    host_id: int | None,
    service_id: int | None,
    endpoint_id: int | None,
) -> str:
    """Build the rollup dimension key for one raw sample's scope.

    The raw sample table stores the scope in four columns while the rollup
    tables collapse it into one string, so the same function must build the key
    on every write and on every read — a second, slightly different
    implementation would split one series into two.
    """

    def _part(value: int | None) -> int:
        return int(value) if value is not None else 0

    return "|".join(
        (
            environment or "PRODUCTION",
            f"host={_part(host_id)}",
            f"service={_part(service_id)}",
            f"endpoint={_part(endpoint_id)}",
        )
    )


@dataclass(frozen=True, slots=True)
class RollupBucket:
    """One aggregated bucket ready to be written to a rollup table."""

    metric_key: str
    dimension_key: str
    bucket_at: datetime.datetime
    avg_value: float
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

    # ------------------------------------------------------------------
    # Rollups (written by the scheduler; the tables are never read raw)
    # ------------------------------------------------------------------
    async def aggregate_raw_buckets(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> list[RollupBucket]:
        """Aggregate raw samples into hourly buckets.

        The bucket is computed in the database because ``collected_at`` is
        ``timestamptz``: truncating in Python would silently use the server's
        local timezone and put points in the wrong hour.

        The bucket is computed in a sub-query on purpose. Writing
        ``date_trunc`` in both the select list and the ``GROUP BY`` renders two
        *different* bind parameters, and PostgreSQL rejects the grouping
        because ``$1`` and ``$6`` are not the same expression tree.
        """
        rows = (
            await self._session.execute(
                text(_AGGREGATE_RAW_SQL), {"start": start, "end": end}
            )
        ).all()
        buckets: list[RollupBucket] = []
        for row in rows:
            (
                metric_key,
                host_id,
                service_id,
                endpoint_id,
                environment,
                bucket_at,
                count,
                sum_value,
                min_value,
                max_value,
            ) = row
            sample_count = int(count or 0)
            if sample_count <= 0:
                continue
            total = float(sum_value or 0.0)
            buckets.append(
                RollupBucket(
                    metric_key=str(metric_key),
                    dimension_key=build_dimension_key(
                        environment=str(environment or ""),
                        host_id=host_id,
                        service_id=service_id,
                        endpoint_id=endpoint_id,
                    ),
                    bucket_at=bucket_at,
                    avg_value=total / sample_count,
                    min_value=float(min_value if min_value is not None else 0.0),
                    max_value=float(max_value if max_value is not None else 0.0),
                    sum_value=total,
                    sample_count=sample_count,
                )
            )
        return buckets

    async def aggregate_hourly_buckets(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> list[RollupBucket]:
        """Aggregate hourly rollups into daily buckets.

        Daily rollups are built from the hourly table, not from the raw samples:
        raw samples are purged after seven days while the daily table keeps 180,
        so a rebuild of a month old day must still have its source available.
        """
        # Same reason as above for the sub-query: the bucket expression must be
        # bound once, not once per clause.
        rows = (
            await self._session.execute(
                text(_AGGREGATE_HOURLY_SQL), {"start": start, "end": end}
            )
        ).all()
        buckets: list[RollupBucket] = []
        for row in rows:
            metric_key, dimension_key, bucket_at, count, sum_value, min_value, max_value = row
            sample_count = int(count or 0)
            if sample_count <= 0:
                continue
            total = float(sum_value or 0.0)
            buckets.append(
                RollupBucket(
                    metric_key=str(metric_key),
                    dimension_key=str(dimension_key),
                    bucket_at=bucket_at,
                    avg_value=total / sample_count,
                    min_value=float(min_value if min_value is not None else 0.0),
                    max_value=float(max_value if max_value is not None else 0.0),
                    sum_value=total,
                    sample_count=sample_count,
                )
            )
        return buckets

    async def upsert_hourly_buckets(self, buckets: list[RollupBucket]) -> int:
        return await self._upsert_buckets(OpsMetricHourly, buckets)

    async def upsert_daily_buckets(self, buckets: list[RollupBucket]) -> int:
        return await self._upsert_buckets(OpsMetricDaily, buckets)

    async def _upsert_buckets(self, model: Any, buckets: list[RollupBucket]) -> int:
        if not buckets:
            return 0
        now = datetime.datetime.now(datetime.UTC)
        rows = [
            {
                "id": new_id(),
                "metric_key": bucket.metric_key,
                "dimension_key": bucket.dimension_key,
                "bucket_at": bucket.bucket_at,
                "avg_value": bucket.avg_value,
                "min_value": bucket.min_value,
                "max_value": bucket.max_value,
                "sum_value": bucket.sum_value,
                "sample_count": bucket.sample_count,
                "created_at": now,
            }
            for bucket in buckets
        ]
        # Re-running a tick must recompute the bucket, not duplicate it: the
        # unique constraint is (metric_key, dimension_key, bucket_at) and the
        # update path overwrites every aggregate column.
        statement = pg_insert(model).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=["metric_key", "dimension_key", "bucket_at"],
            set_={
                "avg_value": statement.excluded.avg_value,
                "min_value": statement.excluded.min_value,
                "max_value": statement.excluded.max_value,
                "sum_value": statement.excluded.sum_value,
                "sample_count": statement.excluded.sample_count,
            },
        )
        await self._session.execute(statement)
        return len(rows)

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
