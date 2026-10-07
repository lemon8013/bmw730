"""app.ops.dashboard — request and response DTOs.

The overview is a read-only projection assembled from several ops tables. It is
total by contract: a counter is ``0`` and a list is empty when there is no data,
never ``null`` and never an error, so an empty monitoring installation still
renders.
"""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, StringId

#: Widget types the frontend can render — a frozen enumeration, not free text.
WIDGET_TYPES: frozenset[str] = frozenset(
    {"STAT", "LINE", "AREA", "BAR", "TABLE", "GAUGE", "TOPN", "TIMELINE"}
)

#: Alert severities always present in the overview breakdown, so a caller can
#: render the breakdown without first guessing which keys exist.
ALERT_SEVERITIES: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})

#: Alert statuses that still need a human: a resolved alert is history.
ACTIVE_ALERT_STATUSES: frozenset[str] = frozenset({"TRIGGERED", "FIRING", "ACKNOWLEDGED"})

#: Service statuses that mean "not healthy". ``MAINTENANCE`` is deliberate
#: silence and ``UNKNOWN`` is missing data, so neither is counted as abnormal.
ABNORMAL_SERVICE_STATUSES: frozenset[str] = frozenset({"DOWN", "DEGRADED"})

HOST_STATUS_ONLINE: str = "ONLINE"
AGENT_STATUS_ONLINE: str = "ONLINE"

#: Window of the availability success rate, in hours.
DEFAULT_AVAILABILITY_WINDOW_HOURS: int = 24
MAX_AVAILABILITY_WINDOW_HOURS: int = 720

#: Number of events the overview returns.
DEFAULT_RECENT_EVENT_LIMIT: int = 10
MAX_RECENT_EVENT_LIMIT: int = 100


class OverviewEventResponse(ApiModel):
    """One of the most recent operations events."""

    id: StringId
    event_id: str
    event_type: str
    source: str
    severity: str
    message: str | None = None
    occurred_at: datetime.datetime


class OverviewResponse(ApiModel):
    """The operations overview."""

    host_count: int = 0
    online_host_count: int = 0
    service_count: int = 0
    abnormal_service_count: int = 0
    active_alert_count: int = 0
    alerts_by_severity: dict[str, int] = Field(default_factory=dict)
    agent_online_count: int = 0
    availability_success_rate: float = 0.0
    availability_check_count: int = 0
    availability_window_hours: int = DEFAULT_AVAILABILITY_WINDOW_HOURS
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_events: list[OverviewEventResponse] = Field(default_factory=list)
    generated_at: datetime.datetime


class DashboardCreateRequest(ApiModel):
    """Create a dashboard."""

    dashboard_code: str
    name: str
    description: str | None = None
    is_default: bool = False


class DashboardUpdateRequest(ApiModel):
    """Update a dashboard."""

    name: str | None = None
    description: str | None = None
    is_default: bool | None = None


class WidgetResponse(ApiModel):
    """A widget on a dashboard."""

    id: StringId
    dashboard_id: StringId
    widget_type: str
    title: str
    metric_key: str | None = None
    options: dict | None = None
    position_x: int
    position_y: int
    width: int
    height: int
    sort_order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DashboardResponse(ApiModel):
    """A dashboard without its widgets."""

    id: StringId
    dashboard_code: str
    name: str
    description: str | None = None
    is_default: bool
    created_by: StringId | None = None
    created_by_username: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DashboardDetailResponse(DashboardResponse):
    """A dashboard together with the widgets it contains."""

    widgets: list[WidgetResponse] = Field(default_factory=list)


class WidgetCreateRequest(ApiModel):
    """Add a widget to a dashboard."""

    widget_type: str
    title: str
    metric_key: str | None = None
    options: dict | None = None
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    sort_order: int = 0


class WidgetUpdateRequest(ApiModel):
    """Update one widget of one dashboard."""

    widget_type: str | None = None
    title: str | None = None
    metric_key: str | None = None
    options: dict | None = None
    position_x: int | None = None
    position_y: int | None = None
    width: int | None = None
    height: int | None = None
    sort_order: int | None = None
