"""app.ops.dashboard — business logic.

The service owns the transaction: every mutation commits at the end and writes
an audit record plus an operation log.

The overview is the one read path that spans several ops modules. It is total by
contract: an empty installation yields zeros and empty lists instead of an
error, because an operator opening the console for the first time must see a
dashboard, not a failure.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.dashboard.model import OpsDashboard, OpsDashboardWidget
from app.ops.dashboard.repository import DashboardRepository
from app.ops.dashboard.schema import (
    ABNORMAL_SERVICE_STATUSES,
    ACTIVE_ALERT_STATUSES,
    AGENT_STATUS_ONLINE,
    ALERT_SEVERITIES,
    HOST_STATUS_ONLINE,
    WIDGET_TYPES,
    DashboardCreateRequest,
    DashboardDetailResponse,
    DashboardResponse,
    DashboardUpdateRequest,
    OverviewEventResponse,
    OverviewResponse,
    WidgetCreateRequest,
    WidgetResponse,
    WidgetUpdateRequest,
)
from app.ops.events.model import OpsEvent
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class DashboardService:
    """Dashboards, widgets and the operations overview."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = DashboardRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def overview(
        self,
        *,
        availability_hours: int,
        recent_event_limit: int,
    ) -> OverviewResponse:
        """Assemble the operations overview."""
        host_count, online_host_count = await self._repository.count_hosts(
            online_status=HOST_STATUS_ONLINE
        )
        service_count, abnormal_service_count = await self._repository.count_services(
            abnormal_statuses=ABNORMAL_SERVICE_STATUSES
        )
        by_severity = await self._repository.count_active_alerts_by_severity(
            active_statuses=ACTIVE_ALERT_STATUSES
        )
        # Every severity is present, so the caller renders a fixed breakdown
        # instead of probing which keys happen to exist today.
        alerts_by_severity = {severity: 0 for severity in sorted(ALERT_SEVERITIES)}
        for severity, count in by_severity.items():
            alerts_by_severity[severity] = count
        agent_online_count = await self._repository.count_online_agents(
            online_status=AGENT_STATUS_ONLINE
        )
        window_start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            hours=availability_hours
        )
        check_count, success_count = await self._repository.aggregate_availability(
            since=window_start
        )
        return OverviewResponse(
            host_count=host_count,
            online_host_count=online_host_count,
            service_count=service_count,
            abnormal_service_count=abnormal_service_count,
            active_alert_count=sum(alerts_by_severity.values()),
            alerts_by_severity=alerts_by_severity,
            agent_online_count=agent_online_count,
            availability_success_rate=(
                success_count / check_count if check_count else 0.0
            ),
            availability_check_count=check_count,
            availability_window_hours=availability_hours,
            recent_event_limit=recent_event_limit,
            recent_events=[
                self._to_event_response(row)
                for row in await self._repository.recent_events(recent_event_limit)
            ],
            generated_at=datetime.datetime.now(datetime.UTC),
        )

    async def list_dashboards(
        self, *, keyword: str | None = None, page: PageParams
    ) -> Page[DashboardResponse]:
        rows, total = await self._repository.list(
            keyword=keyword, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_dashboard(self, dashboard_id: int) -> DashboardDetailResponse:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        return await self._to_detail_response(row)

    async def create_dashboard(
        self, actor: Principal, payload: DashboardCreateRequest
    ) -> DashboardDetailResponse:
        dashboard_code = payload.dashboard_code.strip()
        name = payload.name.strip()
        if not dashboard_code:
            raise ValidationError("dashboard_code is required")
        if not name:
            raise ValidationError("name is required")
        if await self._repository.get_by_code(dashboard_code):
            raise ConflictError("dashboard_code is already used")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            dashboard_code=dashboard_code,
            name=name,
            description=payload.description,
            is_default=payload.is_default,
            created_by=actor.subject_id,
            created_by_username=actor.username,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_DASHBOARD_CREATE",
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
            after_data={"dashboard_code": dashboard_code, "name": name},
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_detail_response(row)

    async def update_dashboard(
        self, actor: Principal, dashboard_id: int, payload: DashboardUpdateRequest
    ) -> DashboardDetailResponse:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        before = {"name": str(row.name), "is_default": bool(row.is_default)}
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_DASHBOARD_UPDATE",
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_detail_response(row)

    async def delete_dashboard(self, actor: Principal, dashboard_id: int) -> None:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        widgets = await self._repository.list_widgets(int(row.id))
        for widget in widgets:
            await self._repository.soft_delete_widget(widget)
        await self._repository.soft_delete(row)
        await self._audit.record(
            action="OPS_DASHBOARD_DELETE",
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
            before_data={"dashboard_code": str(row.dashboard_code)},
            after_data={"deleted_widget_count": len(widgets)},
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def list_widgets(self, dashboard_id: int) -> list[WidgetResponse]:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        return [
            self._to_widget_response(widget)
            for widget in await self._repository.list_widgets(int(row.id))
        ]

    async def create_widget(
        self, actor: Principal, dashboard_id: int, payload: WidgetCreateRequest
    ) -> WidgetResponse:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        widget_type = payload.widget_type.strip().upper()
        if widget_type not in WIDGET_TYPES:
            raise ValidationError(f"widget_type must be one of {sorted(WIDGET_TYPES)}")
        title = payload.title.strip()
        if not title:
            raise ValidationError("title is required")
        now = datetime.datetime.now(datetime.UTC)
        widget = await self._repository.create_widget(
            id=new_id(),
            dashboard_id=int(row.id),
            widget_type=widget_type,
            title=title,
            metric_key=payload.metric_key,
            options=payload.options,
            position_x=payload.position_x,
            position_y=payload.position_y,
            width=payload.width,
            height=payload.height,
            sort_order=payload.sort_order,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_DASHBOARD_WIDGET_CREATE",
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
            after_data={"dashboard_id": str(int(row.id)), "widget_type": widget_type},
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_WIDGET_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
        )
        await self._session.commit()
        return self._to_widget_response(widget)

    async def update_widget(
        self,
        actor: Principal,
        dashboard_id: int,
        widget_id: int,
        payload: WidgetUpdateRequest,
    ) -> WidgetResponse:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        widget = await self._repository.get_widget(int(row.id), widget_id)
        if widget is None:
            raise NotFoundError("widget not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "widget_type" in changes:
            widget_type = str(changes["widget_type"]).strip().upper()
            if widget_type not in WIDGET_TYPES:
                raise ValidationError(f"widget_type must be one of {sorted(WIDGET_TYPES)}")
            changes["widget_type"] = widget_type
        before = {"widget_type": str(widget.widget_type), "title": str(widget.title)}
        await self._repository.update_widget(widget, **changes)
        widget.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_DASHBOARD_WIDGET_UPDATE",
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_WIDGET_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
        )
        await self._session.commit()
        return self._to_widget_response(widget)

    async def delete_widget(
        self, actor: Principal, dashboard_id: int, widget_id: int
    ) -> None:
        row = await self._repository.get(dashboard_id)
        if row is None:
            raise NotFoundError("dashboard not found")
        widget = await self._repository.get_widget(int(row.id), widget_id)
        if widget is None:
            raise NotFoundError("widget not found")
        await self._repository.soft_delete_widget(widget)
        await self._audit.record(
            action="OPS_DASHBOARD_WIDGET_DELETE",
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
            before_data={"title": str(widget.title)},
        )
        await write_operation_log(
            self._session,
            operation="OPS_DASHBOARD_WIDGET_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_dashboard_widget",
            resource_id=int(widget.id),
        )
        await self._session.commit()

    def _to_response(self, row: OpsDashboard) -> DashboardResponse:
        return DashboardResponse(
            id=str(int(row.id)),
            dashboard_code=str(row.dashboard_code),
            name=str(row.name),
            description=row.description,
            is_default=bool(row.is_default),
            created_by=str(int(row.created_by)) if row.created_by else None,
            created_by_username=row.created_by_username,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _to_detail_response(self, row: OpsDashboard) -> DashboardDetailResponse:
        """Render a dashboard together with the widgets it currently contains."""
        widgets = await self._repository.list_widgets(int(row.id))
        return DashboardDetailResponse(
            **self._to_response(row).model_dump(),
            widgets=[self._to_widget_response(widget) for widget in widgets],
        )

    def _to_widget_response(self, row: OpsDashboardWidget) -> WidgetResponse:
        return WidgetResponse(
            id=str(int(row.id)),
            dashboard_id=str(int(row.dashboard_id)),
            widget_type=str(row.widget_type),
            title=str(row.title),
            metric_key=row.metric_key,
            options=row.options,
            position_x=int(row.position_x or 0),
            position_y=int(row.position_y or 0),
            width=int(row.width or 0),
            height=int(row.height or 0),
            sort_order=int(row.sort_order or 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_event_response(self, row: OpsEvent) -> OverviewEventResponse:
        return OverviewEventResponse(
            id=str(int(row.id)),
            event_id=str(row.event_id),
            event_type=str(row.event_type),
            source=str(row.source),
            severity=str(row.severity),
            message=row.message,
            occurred_at=row.occurred_at,
        )
