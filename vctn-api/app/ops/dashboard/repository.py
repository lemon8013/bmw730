"""app.ops.dashboard — data access.

Two responsibilities live here: CRUD of dashboards and widgets, and the
read-only aggregations behind the overview. Repository methods never commit and
never decide policy — which status counts as abnormal or which alert counts as
active is declared in :mod:`app.ops.dashboard.schema` and applied by the service.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.agents.model import OpsAgent
from app.ops.alerts.model import OpsAlert
from app.ops.availability.model import OpsAvailabilityResult
from app.ops.dashboard.model import OpsDashboard, OpsDashboardWidget
from app.ops.events.model import OpsEvent
from app.ops.hosts.model import OpsHost
from app.ops.services.model import OpsService


class DashboardRepository:
    """Data access for dashboards, widgets and the overview aggregations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsDashboard], int]:
        base = select(OpsDashboard).where(OpsDashboard.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsDashboard.dashboard_code.ilike(f"%{keyword}%")
                | OpsDashboard.name.ilike(f"%{keyword}%")
            )
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
                    base.order_by(OpsDashboard.dashboard_code.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, dashboard_id: int) -> OpsDashboard | None:
        row = await self._session.get(OpsDashboard, dashboard_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_code(self, dashboard_code: str) -> OpsDashboard | None:
        result = await self._session.execute(
            select(OpsDashboard).where(
                OpsDashboard.dashboard_code == dashboard_code,
                OpsDashboard.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsDashboard:
        row = OpsDashboard(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsDashboard, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: OpsDashboard) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_widgets(self, dashboard_id: int) -> list[OpsDashboardWidget]:
        rows = (
            await self._session.execute(
                select(OpsDashboardWidget)
                .where(
                    OpsDashboardWidget.dashboard_id == dashboard_id,
                    OpsDashboardWidget.deleted_at.is_(None),
                )
                .order_by(OpsDashboardWidget.sort_order.asc(), OpsDashboardWidget.id.asc())
            )
        ).scalars()
        return list(rows)

    async def get_widget(self, dashboard_id: int, widget_id: int) -> OpsDashboardWidget | None:
        row = await self._session.get(OpsDashboardWidget, widget_id)
        if row is None or row.deleted_at is not None or row.dashboard_id != dashboard_id:
            return None
        return row

    async def create_widget(self, **fields: object) -> OpsDashboardWidget:
        row = OpsDashboardWidget(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_widget(self, row: OpsDashboardWidget, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete_widget(self, row: OpsDashboardWidget) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def count_hosts(self, *, online_status: str) -> tuple[int, int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(OpsHost)
                    .where(OpsHost.deleted_at.is_(None))
                )
            ).scalar_one()
        )
        online = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(OpsHost)
                    .where(OpsHost.deleted_at.is_(None), OpsHost.status == online_status)
                )
            ).scalar_one()
        )
        return total, online

    async def count_services(self, *, abnormal_statuses: frozenset[str]) -> tuple[int, int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(OpsService)
                    .where(OpsService.deleted_at.is_(None))
                )
            ).scalar_one()
        )
        abnormal = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(OpsService)
                    .where(
                        OpsService.deleted_at.is_(None),
                        OpsService.status.in_(sorted(abnormal_statuses)),
                    )
                )
            ).scalar_one()
        )
        return total, abnormal

    async def count_active_alerts_by_severity(
        self, *, active_statuses: frozenset[str]
    ) -> dict[str, int]:
        rows = (
            await self._session.execute(
                select(OpsAlert.severity, func.count())
                .where(OpsAlert.status.in_(sorted(active_statuses)))
                .group_by(OpsAlert.severity)
            )
        ).all()
        return {str(severity): int(count) for severity, count in rows}

    async def count_online_agents(self, *, online_status: str) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(OpsAgent)
                    .where(
                        OpsAgent.deleted_at.is_(None),
                        OpsAgent.enabled.is_(True),
                        OpsAgent.status == online_status,
                    )
                )
            ).scalar_one()
        )

    async def aggregate_availability(
        self, *, since: datetime.datetime
    ) -> tuple[int, int]:
        """Return the probe count and the successful probe count in a window."""
        row = (
            await self._session.execute(
                select(
                    func.count(),
                    func.sum(sa.case((OpsAvailabilityResult.success.is_(True), 1), else_=0)),
                ).where(OpsAvailabilityResult.checked_at >= since)
            )
        ).one()
        total = int(row[0] or 0)
        success = int(row[1] or 0)
        return total, success

    async def recent_events(self, limit: int) -> list[OpsEvent]:
        rows = (
            await self._session.execute(
                select(OpsEvent).order_by(OpsEvent.occurred_at.desc()).limit(limit)
            )
        ).scalars()
        return list(rows)
