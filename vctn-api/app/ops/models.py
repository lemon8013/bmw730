"""Every ops ORM model, imported in one place.

Alembic's autogenerate compares ``Base.metadata`` against the live schema, and
a foreign key written as a string is only resolved once the referenced class has
been imported. Importing this module therefore guarantees that a migration sees
the complete ops schema, including cross-module references such as
``ops_host.agent_id -> ops_agent.id``.
"""

from __future__ import annotations

from app.ops.agents.model import OpsAgent, OpsAgentHeartbeat
from app.ops.alerts.model import (
    OpsAlert,
    OpsAlertHistory,
    OpsAlertNotification,
    OpsAlertRule,
)
from app.ops.apis.model import OpsEndpoint
from app.ops.audit.model import OpsOperationRecord
from app.ops.availability.model import OpsAvailabilityCheck, OpsAvailabilityResult
from app.ops.dashboard.model import OpsDashboard, OpsDashboardWidget
from app.ops.events.model import OpsEvent
from app.ops.hosts.model import OpsEnvironment, OpsHost, OpsHostGroup
from app.ops.maintenance.model import OpsMaintenanceWindow
from app.ops.metrics.model import (
    OpsMetricDaily,
    OpsMetricDefinition,
    OpsMetricHourly,
    OpsMetricSample,
    OpsMonitor,
)
from app.ops.notifications.model import OpsNotificationChannel, OpsNotificationGroup
from app.ops.services.model import OpsService, OpsServiceDependency

__all__ = [
    "OpsAgent",
    "OpsAgentHeartbeat",
    "OpsAlert",
    "OpsAlertHistory",
    "OpsAlertNotification",
    "OpsAlertRule",
    "OpsAvailabilityCheck",
    "OpsAvailabilityResult",
    "OpsDashboard",
    "OpsDashboardWidget",
    "OpsEndpoint",
    "OpsEnvironment",
    "OpsEvent",
    "OpsHost",
    "OpsHostGroup",
    "OpsMaintenanceWindow",
    "OpsMetricDaily",
    "OpsMetricDefinition",
    "OpsMetricHourly",
    "OpsMetricSample",
    "OpsMonitor",
    "OpsNotificationChannel",
    "OpsNotificationGroup",
    "OpsOperationRecord",
    "OpsService",
    "OpsServiceDependency",
]
