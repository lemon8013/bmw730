"""app.ops.alerts — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class AlertRuleCreateRequest(ApiModel):
    """Create an alert rule."""

    rule_code: str
    rule_name: str
    alert_type: str
    metric_key: str
    condition: str = "GT"
    threshold: float
    duration_seconds: int = 300
    severity: str = "WARNING"
    scope_type: str = "GLOBAL"
    scope_id: str | None = None
    notification_policy: dict | None = None
    enabled: bool = True


class AlertRuleUpdateRequest(ApiModel):
    """Update an alert rule."""

    rule_name: str | None = None
    alert_type: str | None = None
    metric_key: str | None = None
    condition: str | None = None
    threshold: float | None = None
    duration_seconds: int | None = None
    severity: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    notification_policy: dict | None = None
    enabled: bool | None = None


class AlertRuleResponse(ApiModel):
    """An alert rule."""

    id: StringId
    rule_code: str
    rule_name: str
    alert_type: str
    metric_key: str
    condition: str
    threshold: float
    duration_seconds: int
    severity: str
    scope_type: str
    scope_id: StringId | None = None
    notification_policy: dict | None = None
    enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AlertResponse(ApiModel):
    """An alert instance."""

    id: StringId
    fingerprint: str
    rule_id: StringId | None = None
    alert_type: str
    severity: str
    status: str
    resource_type: str | None = None
    resource_id: StringId | None = None
    host_id: StringId | None = None
    service_id: StringId | None = None
    metric_key: str | None = None
    metric_value: float | None = None
    threshold: float | None = None
    description: str | None = None
    trace_id: str | None = None
    triggered_at: datetime.datetime
    acknowledged_at: datetime.datetime | None = None
    acknowledged_by: StringId | None = None
    silenced_until: datetime.datetime | None = None
    silence_reason: str | None = None
    resolved_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AlertAckRequest(ApiModel):
    """Acknowledge an alert."""

    note: str | None = None


class AlertSilenceRequest(ApiModel):
    """Silence an alert."""

    silence_minutes: int
    silence_reason: str


class AlertResolveRequest(ApiModel):
    """Resolve an alert."""

    note: str | None = None


class AlertEvaluationResponse(ApiModel):
    """The outcome of one evaluation run."""

    evaluated_rules: int
    firing: int
    resolved: int
    failed_rules: int


class AlertNotificationResponse(ApiModel):
    """One notification attempt recorded for one alert."""

    id: StringId
    alert_id: StringId
    channel_id: StringId | None = None
    channel_code: str
    receiver: str | None = None
    status: str
    retry_count: int
    sent_at: datetime.datetime | None = None
    error_message: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
