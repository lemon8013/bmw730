"""app.ops.reports — request and response DTOs.

The reports are **read-only projections**: they aggregate the tables the
collectors already write and never create a table of their own, so there is no
migration to keep in step.

Every report is *total by contract* the same way the overview is: an empty
installation yields zeros and empty lists instead of an error, because an
operator opening the console for the first time must see a report rather than a
failure.
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId

#: Severity levels always present in the trend breakdown, so a caller renders a
#: fixed set of series instead of probing which keys happen to exist today.
REPORT_SEVERITIES: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})

#: Alert statuses that still need a human.
ACTIVE_ALERT_STATUSES: frozenset[str] = frozenset({"TRIGGERED", "FIRING", "ACKNOWLEDGED"})

#: Service statuses that mean "not healthy".
ABNORMAL_SERVICE_STATUSES: frozenset[str] = frozenset({"DOWN", "DEGRADED"})

HOST_STATUS_ONLINE: str = "ONLINE"
AGENT_STATUS_ONLINE: str = "ONLINE"

#: Default reporting window, in days.
DEFAULT_REPORT_DAYS: int = 7
#: Longest window a report may cover — the raw sample retention is 7 days and
#: the daily rollup retention is 180, so a longer window would silently lose
#: its middle.
MAX_REPORT_DAYS: int = 180

#: Default / maximum number of rows of the alert ranking.
DEFAULT_RANKING_LIMIT: int = 10
MAX_RANKING_LIMIT: int = 100

#: The reports the CSV export can render.
EXPORTABLE_REPORTS: frozenset[str] = frozenset(
    {"summary", "alert-trend", "alert-ranking", "availability", "host-status"}
)

#: Severity rank used to collapse a group of alerts to its worst level.
SEVERITY_RANK: dict[int, str] = {4: "CRITICAL", 3: "ERROR", 2: "WARNING", 1: "INFO"}


class ReportWindow(ApiModel):
    """The window a report covers, echoed back so a render can label itself."""

    days: int
    start_at: datetime.datetime
    end_at: datetime.datetime


class HostReport(ApiModel):
    """Host fleet distribution."""

    total: int = 0
    online: int = 0
    by_status: dict[str, int] = {}
    online_rate: float = 0.0


class ServiceReport(ApiModel):
    """Service fleet health."""

    total: int = 0
    abnormal: int = 0
    availability_rate: float = 0.0


class AlertReport(ApiModel):
    """Alert volume and handling quality inside the window."""

    fired: int = 0
    resolved: int = 0
    active: int = 0
    by_severity: dict[str, int] = {}
    resolve_rate: float = 0.0
    #: Mean time to recovery, in seconds. ``null`` when nothing was resolved,
    #: which a report must render as "no data" rather than as zero.
    mttr_seconds: float | None = None


class AvailabilityReport(ApiModel):
    """Availability probes inside the window."""

    check_count: int = 0
    success_rate: float = 0.0
    failure_count: int = 0


class AgentReport(ApiModel):
    """Collection fleet state; not windowed, it is a snapshot of now."""

    total: int = 0
    online: int = 0


class ReportSummaryResponse(ApiModel):
    """The headline numbers of the reporting window."""

    window: ReportWindow
    host: HostReport
    service: ServiceReport
    alert: AlertReport
    availability: AvailabilityReport
    agent: AgentReport
    generated_at: datetime.datetime


class AlertTrendPoint(ApiModel):
    """One day of the alert trend."""

    date: str
    fired: int = 0
    resolved: int = 0
    by_severity: dict[str, int] = {}


class AlertTrendResponse(ApiModel):
    """Daily alert volume.

    Every day of the window is present, including the days that saw nothing:
    a trend chart with holes lies about how quiet the window was.
    """

    window: ReportWindow
    points: list[AlertTrendPoint] = []
    generated_at: datetime.datetime


class AlertRankingRow(ApiModel):
    """One row of the noisiest-resources ranking."""

    rank: int
    resource_type: str
    resource_id: StringId | None = None
    alert_type: str
    total: int = 0
    active: int = 0
    worst_severity: str | None = None
    last_triggered_at: datetime.datetime | None = None


class AlertRankingResponse(ApiModel):
    """The noisiest resources, most alerts first."""

    window: ReportWindow
    rows: list[AlertRankingRow] = []
    generated_at: datetime.datetime


class AvailabilityRow(ApiModel):
    """One availability probe inside the window."""

    check_id: StringId
    check_code: str
    name: str
    target: str
    total: int = 0
    failed: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0


class AvailabilityReportResponse(ApiModel):
    """Per-probe availability, least reliable first."""

    window: ReportWindow
    rows: list[AvailabilityRow] = []
    generated_at: datetime.datetime


class HostStatusRow(ApiModel):
    """One host status bucket."""

    status: str
    count: int = 0
    share: float = 0.0


class HostStatusResponse(ApiModel):
    """Host fleet status distribution."""

    window: ReportWindow
    total: int = 0
    rows: list[HostStatusRow] = []
    generated_at: datetime.datetime


class ReportExportResponse(ApiModel):
    """A rendered CSV document.

    The content travels inside the envelope because every response of this API
    does — the shared client rejects a body with no envelope, so a bare
    ``text/csv`` endpoint would be unreachable from the console.
    """

    report: str
    filename: str
    content_type: str = "text/csv; charset=utf-8"
    content: str
    generated_at: datetime.datetime
