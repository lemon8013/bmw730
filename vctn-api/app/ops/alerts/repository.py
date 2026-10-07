"""app.ops.alerts — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.alerts.model import (
    OpsAlert,
    OpsAlertHistory,
    OpsAlertNotification,
    OpsAlertRule,
)
from app.ops.metrics.model import OpsMetricDaily, OpsMetricHourly, OpsMetricSample

_DAILY_WINDOW = datetime.timedelta(days=7)


class AlertRepository:
    """Read and write access for alert rules, alerts and their history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_rules(
        self,
        *,
        keyword: str | None = None,
        alert_type: str | None = None,
        enabled: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAlertRule], int]:
        base = select(OpsAlertRule).where(OpsAlertRule.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsAlertRule.rule_code.ilike(f"%{keyword}%")
                | OpsAlertRule.rule_name.ilike(f"%{keyword}%")
            )
        if alert_type:
            base = base.where(OpsAlertRule.alert_type == alert_type)
        if enabled is not None:
            base = base.where(OpsAlertRule.enabled == enabled)
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
                    base.order_by(OpsAlertRule.rule_code.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_rule(self, rule_id: int) -> OpsAlertRule | None:
        row = await self._session.get(OpsAlertRule, rule_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_rule_by_code(self, rule_code: str) -> OpsAlertRule | None:
        result = await self._session.execute(
            select(OpsAlertRule).where(
                OpsAlertRule.rule_code == rule_code,
                OpsAlertRule.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_enabled_rules(self) -> list[OpsAlertRule]:
        rows = (
            await self._session.execute(
                select(OpsAlertRule)
                .where(OpsAlertRule.deleted_at.is_(None), OpsAlertRule.enabled.is_(True))
                .order_by(OpsAlertRule.rule_code.asc())
            )
        ).scalars()
        return list(rows)

    async def create_rule(self, **fields: object) -> OpsAlertRule:
        row = OpsAlertRule(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_rule(self, row: OpsAlertRule, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete_rule(self, row: OpsAlertRule) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_alerts(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAlert], int]:
        base = select(OpsAlert)
        if status:
            base = base.where(OpsAlert.status == status)
        if severity:
            base = base.where(OpsAlert.severity == severity)
        if alert_type:
            base = base.where(OpsAlert.alert_type == alert_type)
        if start is not None:
            base = base.where(OpsAlert.triggered_at >= start)
        if end is not None:
            base = base.where(OpsAlert.triggered_at <= end)
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
                    base.order_by(OpsAlert.triggered_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_alert(self, alert_id: int) -> OpsAlert | None:
        return await self._session.get(OpsAlert, alert_id)

    async def get_alert_by_fingerprint(self, fingerprint: str) -> OpsAlert | None:
        result = await self._session.execute(
            select(OpsAlert).where(OpsAlert.fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    async def create_alert(self, **fields: object) -> OpsAlert:
        row = OpsAlert(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_alert(self, row: OpsAlert, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def add_history(self, **fields: object) -> OpsAlertHistory:
        row = OpsAlertHistory(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_notification(self, **fields: object) -> OpsAlertNotification:
        row = OpsAlertNotification(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def window_aggregate(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        host_id: int | None = None,
        service_id: int | None = None,
        endpoint_id: int | None = None,
    ) -> float | None:
        """Average the metric inside the window, preferring a rollup table."""
        duration = end - start
        if duration <= _DAILY_WINDOW:
            return await self._aggregate_samples(
                metric_key=metric_key,
                start=start,
                end=end,
                host_id=host_id,
                service_id=service_id,
                endpoint_id=endpoint_id,
            )
        columns = (
            func.sum(OpsMetricDaily.sum_value),
            func.sum(OpsMetricDaily.sample_count),
        )
        query = select(*columns).where(
            OpsMetricDaily.metric_key == metric_key,
            OpsMetricDaily.bucket_at >= start,
            OpsMetricDaily.bucket_at <= end,
        )
        total, count = (await self._session.execute(query)).one()
        return self._average(total, count)

    async def _aggregate_samples(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        host_id: int | None,
        service_id: int | None,
        endpoint_id: int | None,
    ) -> float | None:
        columns = (
            func.sum(OpsMetricSample.value),
            func.count(OpsMetricSample.id),
        )
        query = select(*columns).where(
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
        total, count = (await self._session.execute(query)).one()
        if count:
            return self._average(total, count)
        return await self._aggregate_hourly(
            metric_key=metric_key,
            start=start,
            end=end,
            host_id=host_id,
            service_id=service_id,
            endpoint_id=endpoint_id,
        )

    async def _aggregate_hourly(
        self,
        *,
        metric_key: str,
        start: datetime.datetime,
        end: datetime.datetime,
        host_id: int | None,
        service_id: int | None,
        endpoint_id: int | None,
    ) -> float | None:
        columns = (
            func.sum(OpsMetricHourly.sum_value),
            func.sum(OpsMetricHourly.sample_count),
        )
        query = select(*columns).where(
            OpsMetricHourly.metric_key == metric_key,
            OpsMetricHourly.bucket_at >= start,
            OpsMetricHourly.bucket_at <= end,
        )
        if host_id is not None:
            query = query.where(OpsMetricHourly.dimension_key.contains(f"host_id={host_id}"))
        if service_id is not None:
            query = query.where(
                OpsMetricHourly.dimension_key.contains(f"service_id={service_id}")
            )
        if endpoint_id is not None:
            query = query.where(
                OpsMetricHourly.dimension_key.contains(f"endpoint_id={endpoint_id}")
            )
        total, count = (await self._session.execute(query)).one()
        return self._average(total, count)

    @staticmethod
    def _average(total: object, count: object) -> float | None:
        samples = int(count or 0)
        if samples <= 0:
            return None
        return float(total or 0.0) / samples
