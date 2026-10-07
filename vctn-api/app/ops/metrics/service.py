"""app.ops.metrics — business logic.

The service validates UTC ranges and sample contracts. Sample ingestion is a
single audited transaction; repositories never commit.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.metrics.model import OpsMetricDefinition
from app.ops.metrics.repository import MetricRepository, MetricSeriesValue
from app.ops.metrics.schema import (
    MetricDefinitionResponse,
    MetricSamplesCreateRequest,
    MetricSamplesCreateResponse,
    MetricSeriesPoint,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

_RAW_RANGE = datetime.timedelta(hours=6)
_HOURLY_RANGE = datetime.timedelta(days=7)


class MetricService:
    """Metric catalogue, ingestion and time-series queries."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = MetricRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_definitions(
        self,
        *,
        keyword: str | None = None,
        metric_type: str | None = None,
        page: PageParams,
    ) -> Page[MetricDefinitionResponse]:
        rows, total = await self._repository.list_definitions(
            keyword=keyword,
            metric_type=metric_type,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_definition_response(row) for row in rows],
            total=total,
            params=page,
        )

    async def get_series(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        step: str,
        host_id: int | None = None,
        service_id: int | None = None,
        endpoint_id: int | None = None,
    ) -> list[MetricSeriesPoint]:
        key = metric_key.strip()
        if not key:
            raise ValidationError("metric_key is required")
        if await self._repository.get_definition_by_key(key) is None:
            raise NotFoundError("metric definition not found")
        start_utc = self._as_utc(start, field="start")
        end_utc = self._as_utc(end, field="end")
        if start_utc >= end_utc:
            raise ValidationError("start must be earlier than end")
        step_seconds = self._parse_step(step)
        duration = end_utc - start_utc
        dimension_key = self._dimension_key(
            host_id=host_id,
            service_id=service_id,
            endpoint_id=endpoint_id,
        )
        if duration <= _RAW_RANGE:
            source_seconds = 1
            values = await self._repository.list_raw_series(
                metric_key=key,
                start=start_utc,
                end=end_utc,
                host_id=host_id,
                service_id=service_id,
                endpoint_id=endpoint_id,
            )
        elif duration <= _HOURLY_RANGE:
            source_seconds = 3600
            values = await self._repository.list_hourly_series(
                metric_key=key,
                start=start_utc,
                end=end_utc,
                dimension_key=dimension_key,
            )
        else:
            source_seconds = 86400
            values = await self._repository.list_daily_series(
                metric_key=key,
                start=start_utc,
                end=end_utc,
                dimension_key=dimension_key,
            )
        return self._resample(values, max(step_seconds, source_seconds))

    async def create_samples(
        self, actor: Principal, payload: MetricSamplesCreateRequest
    ) -> MetricSamplesCreateResponse:
        if not payload.samples:
            raise ValidationError("samples must not be empty")
        normalized: list[dict[str, object]] = []
        metric_keys: set[str] = set()
        now = datetime.datetime.now(datetime.UTC)
        for sample in payload.samples:
            metric_key = sample.metric_key.strip()
            if not metric_key:
                raise ValidationError("metric_key is required")
            metric_keys.add(metric_key)
            environment = sample.environment.strip()
            if not environment:
                raise ValidationError("environment is required")
            normalized.append(
                {
                    "id": new_id(),
                    "metric_key": metric_key,
                    "host_id": int(sample.host_id) if sample.host_id else None,
                    "service_id": int(sample.service_id) if sample.service_id else None,
                    "endpoint_id": int(sample.endpoint_id) if sample.endpoint_id else None,
                    "environment": environment,
                    "value": sample.value,
                    "labels": sample.labels,
                    "collected_at": self._as_utc(sample.collected_at, field="collected_at"),
                    "created_at": now,
                }
            )
        known_keys = await self._repository.find_definition_keys(metric_keys)
        if known_keys != metric_keys:
            raise ValidationError("one or more metric_key values are not defined")
        rows = await self._repository.create_samples(normalized)
        await self._audit.record(
            action="OPS_METRIC_SAMPLE_CREATE",
            actor=actor,
            resource_type="ops_metric_sample",
            after_data={"count": len(rows), "metric_keys": sorted(metric_keys)},
        )
        await write_operation_log(
            self._session,
            operation="OPS_METRIC_SAMPLE_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_metric_sample",
            metadata={"count": len(rows)},
        )
        await self._session.commit()
        return MetricSamplesCreateResponse(
            accepted=len(rows),
            sample_ids=[str(int(row.id)) for row in rows],
        )

    @staticmethod
    def _as_utc(value: datetime.datetime, *, field: str) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{field} must include a UTC offset")
        return value.astimezone(datetime.UTC)

    @staticmethod
    def _parse_step(step: str) -> int:
        raw = step.strip().lower()
        if not raw:
            raise ValidationError("step is required")
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if raw.isdigit():
            seconds = int(raw)
        else:
            multiplier = units.get(raw[-1])
            number = raw[:-1]
            if multiplier is None or not number.isdigit():
                raise ValidationError("step must be seconds or use s/m/h/d suffix")
            seconds = int(number) * multiplier
        if seconds <= 0:
            raise ValidationError("step must be greater than 0")
        return seconds

    @staticmethod
    def _dimension_key(
        *, host_id: int | None, service_id: int | None, endpoint_id: int | None
    ) -> str | None:
        parts = []
        if host_id is not None:
            parts.append(f"host_id={host_id}")
        if service_id is not None:
            parts.append(f"service_id={service_id}")
        if endpoint_id is not None:
            parts.append(f"endpoint_id={endpoint_id}")
        return "|".join(parts) if parts else None

    @staticmethod
    def _resample(
        values: list[MetricSeriesValue], step_seconds: int
    ) -> list[MetricSeriesPoint]:
        buckets: dict[int, dict[str, float | int]] = {}
        for point in values:
            timestamp = point.timestamp.astimezone(datetime.UTC)
            bucket = int(timestamp.timestamp()) // step_seconds * step_seconds
            current = buckets.setdefault(
                bucket,
                {
                    "sum": 0.0,
                    "count": 0,
                    "min": point.min_value,
                    "max": point.max_value,
                },
            )
            current["sum"] = float(current["sum"]) + point.sum_value
            current["count"] = int(current["count"]) + point.sample_count
            current["min"] = min(float(current["min"]), point.min_value)
            current["max"] = max(float(current["max"]), point.max_value)
        result: list[MetricSeriesPoint] = []
        for bucket, values_by_bucket in sorted(buckets.items()):
            count = int(values_by_bucket["count"])
            total = float(values_by_bucket["sum"])
            result.append(
                MetricSeriesPoint(
                    timestamp=datetime.datetime.fromtimestamp(bucket, datetime.UTC),
                    value=total / count,
                    min_value=float(values_by_bucket["min"]),
                    max_value=float(values_by_bucket["max"]),
                    sum_value=total,
                    sample_count=count,
                )
            )
        return result

    @staticmethod
    def _to_definition_response(row: OpsMetricDefinition) -> MetricDefinitionResponse:
        return MetricDefinitionResponse(
            id=str(int(row.id)),
            metric_key=str(row.metric_key),
            metric_name=str(row.metric_name),
            metric_type=str(row.metric_type),
            unit=row.unit,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
