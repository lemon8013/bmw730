"""app.ops.alerts — business logic.

The service owns the transaction: alert state transitions write a history row,
an audit record and an operation log, and commit at the end. Resolving an alert
is only allowed when the alert is acknowledged or when its rule no longer
matches, so a ``RESOLVED`` status can never be forged.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.ops.alerts.evaluator import (
    ALERT_SCOPE_TYPES,
    ALERT_SEVERITIES,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
    CONDITION_OPERATORS,
    AlertEvaluator,
    matches_condition,
)
from app.ops.alerts.model import OpsAlert, OpsAlertRule
from app.ops.alerts.repository import AlertRepository
from app.ops.alerts.schema import (
    AlertAckRequest,
    AlertEvaluationResponse,
    AlertResolveRequest,
    AlertResponse,
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
    AlertSilenceRequest,
)
from app.ops.audit.recorder import OpsAuditRecorder
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

_RESOLVABLE_STATUSES: frozenset[str] = frozenset({ALERT_STATUS_ACKNOWLEDGED})


class AlertService:
    """Alert rules, alert instances and their lifecycle transitions."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AlertRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_rules(
        self,
        *,
        keyword: str | None = None,
        alert_type: str | None = None,
        enabled: bool | None = None,
        page: PageParams,
    ) -> Page[AlertRuleResponse]:
        rows, total = await self._repository.list_rules(
            keyword=keyword,
            alert_type=alert_type,
            enabled=enabled,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_rule_response(row) for row in rows], total=total, params=page
        )

    async def create_rule(
        self, actor: Principal, payload: AlertRuleCreateRequest
    ) -> AlertRuleResponse:
        rule_code = payload.rule_code.strip()
        if not rule_code:
            raise ValidationError("rule_code is required")
        if not payload.rule_name.strip():
            raise ValidationError("rule_name is required")
        if not payload.alert_type.strip():
            raise ValidationError("alert_type is required")
        if not payload.metric_key.strip():
            raise ValidationError("metric_key is required")
        self._validate_condition(payload.condition)
        self._validate_duration(payload.duration_seconds)
        self._validate_severity(payload.severity)
        self._validate_scope_type(payload.scope_type)
        if await self._repository.get_rule_by_code(rule_code):
            raise ConflictError("rule_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create_rule(
            id=new_id(),
            rule_code=rule_code,
            rule_name=payload.rule_name,
            alert_type=payload.alert_type,
            metric_key=payload.metric_key,
            condition=payload.condition,
            threshold=payload.threshold,
            duration_seconds=payload.duration_seconds,
            severity=payload.severity,
            scope_type=payload.scope_type,
            scope_id=int(payload.scope_id) if payload.scope_id else None,
            notification_policy=payload.notification_policy,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_ALERT_RULE_CREATE",
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
            after_data={"rule_code": rule_code, "threshold": payload.threshold},
        )
        await write_operation_log(
            self._session,
            operation="OPS_ALERT_RULE_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_rule_response(row)

    async def update_rule(
        self, actor: Principal, rule_id: int, payload: AlertRuleUpdateRequest
    ) -> AlertRuleResponse:
        row = await self._repository.get_rule(rule_id)
        if row is None:
            raise NotFoundError("alert rule not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "condition" in changes:
            self._validate_condition(str(changes["condition"]))
        if "duration_seconds" in changes:
            self._validate_duration(int(changes["duration_seconds"]))
        if "severity" in changes:
            self._validate_severity(str(changes["severity"]))
        if "scope_type" in changes:
            self._validate_scope_type(str(changes["scope_type"]))
        if "scope_id" in changes:
            changes["scope_id"] = int(changes["scope_id"]) if changes["scope_id"] else None
        before = {
            "threshold": row.threshold,
            "condition": row.condition,
            "duration_seconds": row.duration_seconds,
            "enabled": row.enabled,
        }
        await self._repository.update_rule(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_ALERT_RULE_UPDATE",
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_ALERT_RULE_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_rule_response(row)

    async def delete_rule(self, actor: Principal, rule_id: int) -> None:
        row = await self._repository.get_rule(rule_id)
        if row is None:
            raise NotFoundError("alert rule not found")
        await self._repository.soft_delete_rule(row)
        await self._audit.record(
            action="OPS_ALERT_RULE_DELETE",
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat() if row.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_ALERT_RULE_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert_rule",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def list_alerts(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[AlertResponse]:
        start_utc = self._as_utc(start, field="start") if start is not None else None
        end_utc = self._as_utc(end, field="end") if end is not None else None
        if start_utc is not None and end_utc is not None and start_utc > end_utc:
            raise ValidationError("start must not be later than end")
        rows, total = await self._repository.list_alerts(
            status=status,
            severity=severity,
            alert_type=alert_type,
            start=start_utc,
            end=end_utc,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_alert_response(row) for row in rows], total=total, params=page
        )

    async def get_alert(self, alert_id: int) -> AlertResponse:
        row = await self._repository.get_alert(alert_id)
        if row is None:
            raise NotFoundError("alert not found")
        return self._to_alert_response(row)

    async def acknowledge_alert(
        self, actor: Principal, alert_id: int, payload: AlertAckRequest
    ) -> AlertResponse:
        row = await self._get_alert_or_fail(alert_id)
        if row.status == ALERT_STATUS_RESOLVED:
            raise ConflictError("a resolved alert cannot be acknowledged")
        if row.status == ALERT_STATUS_ACKNOWLEDGED:
            raise ConflictError("alert is already acknowledged")
        now = datetime.datetime.now(datetime.UTC)
        await self._transition(
            row,
            ALERT_STATUS_ACKNOWLEDGED,
            now,
            actor=actor,
            note=payload.note,
        )
        await self._repository.update_alert(
            row,
            acknowledged_at=now,
            acknowledged_by=actor.subject_id,
            updated_at=now,
        )
        await self._commit_transition(
            actor=actor,
            action="OPS_ALERT_ACK",
            alert=row,
            note=payload.note,
        )
        return self._to_alert_response(row)

    async def silence_alert(
        self, actor: Principal, alert_id: int, payload: AlertSilenceRequest
    ) -> AlertResponse:
        row = await self._get_alert_or_fail(alert_id)
        if payload.silence_minutes <= 0:
            raise ValidationError("silence_minutes must be greater than 0")
        reason = payload.silence_reason.strip()
        if not reason:
            raise ValidationError("silence_reason is required")
        now = datetime.datetime.now(datetime.UTC)
        silenced_until = now + datetime.timedelta(minutes=payload.silence_minutes)
        # 静默只压制通知：状态维度和静默维度互不干扰，所以这里不动 status。
        await self._repository.update_alert(
            row,
            silenced_until=silenced_until,
            silence_reason=reason,
            updated_at=now,
        )
        await self._repository.add_history(
            id=new_id(),
            alert_id=int(row.id),
            from_status=str(row.status),
            to_status=str(row.status),
            actor_id=actor.subject_id,
            actor_username=actor.username,
            note=f"silenced until {silenced_until.isoformat()}: {reason}",
            created_at=now,
        )
        await self._audit.record(
            action="OPS_ALERT_SILENCE",
            actor=actor,
            resource_type="ops_alert",
            resource_id=int(row.id),
            after_data={
                "silenced_until": silenced_until.isoformat(),
                "silence_reason": reason,
            },
        )
        await write_operation_log(
            self._session,
            operation="OPS_ALERT_SILENCE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_alert_response(row)

    async def resolve_alert(
        self, actor: Principal, alert_id: int, payload: AlertResolveRequest
    ) -> AlertResponse:
        row = await self._get_alert_or_fail(alert_id)
        if row.status == ALERT_STATUS_RESOLVED:
            raise ConflictError("alert is already resolved")
        still_firing = await self._rule_still_matches(row)
        if row.status not in _RESOLVABLE_STATUSES and still_firing:
            # 规则仍命中且告警未被确认时置 RESOLVED 就是伪造恢复，这里拒绝。
            raise BusinessRuleError("alert can only be resolved once acknowledged or cleared")
        now = datetime.datetime.now(datetime.UTC)
        await self._transition(
            row,
            ALERT_STATUS_RESOLVED,
            now,
            actor=actor,
            note=payload.note,
        )
        await self._repository.update_alert(row, resolved_at=now, updated_at=now)
        await self._commit_transition(
            actor=actor,
            action="OPS_ALERT_RESOLVE",
            alert=row,
            note=payload.note,
        )
        return self._to_alert_response(row)

    async def evaluate(self, actor: Principal) -> AlertEvaluationResponse:
        now = datetime.datetime.now(datetime.UTC)
        outcome = await AlertEvaluator(self._session).evaluate(now)
        await self._audit.record(
            action="OPS_ALERT_EVALUATE",
            actor=actor,
            resource_type="ops_alert_rule",
            after_data=dict(outcome),
        )
        await write_operation_log(
            self._session,
            operation="OPS_ALERT_EVALUATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert_rule",
            metadata=dict(outcome),
        )
        await self._session.commit()
        return AlertEvaluationResponse(**outcome)

    async def _rule_still_matches(self, alert: OpsAlert) -> bool:
        if alert.rule_id is None:
            return False
        rule = await self._repository.get_rule(int(alert.rule_id))
        if rule is None or not bool(rule.enabled):
            return False
        now = datetime.datetime.now(datetime.UTC)
        start = now - datetime.timedelta(seconds=int(rule.duration_seconds or 0))
        value = await self._repository.window_aggregate(
            metric_key=str(rule.metric_key),
            start=start,
            end=now,
            host_id=int(alert.host_id) if alert.host_id is not None else None,
            service_id=int(alert.service_id) if alert.service_id is not None else None,
            endpoint_id=None,
        )
        if value is None:
            return False
        return matches_condition(
            condition=str(rule.condition),
            value=value,
            threshold=float(rule.threshold),
        )

    async def _get_alert_or_fail(self, alert_id: int) -> OpsAlert:
        row = await self._repository.get_alert(alert_id)
        if row is None:
            raise NotFoundError("alert not found")
        return row

    async def _transition(
        self,
        alert: OpsAlert,
        to_status: str,
        now: datetime.datetime,
        *,
        actor: Principal,
        note: str | None,
    ) -> None:
        from_status = str(alert.status)
        await self._repository.update_alert(alert, status=to_status, updated_at=now)
        await self._repository.add_history(
            id=new_id(),
            alert_id=int(alert.id),
            from_status=from_status,
            to_status=to_status,
            actor_id=actor.subject_id,
            actor_username=actor.username,
            note=note,
            created_at=now,
        )

    async def _commit_transition(
        self, *, actor: Principal, action: str, alert: OpsAlert, note: str | None
    ) -> None:
        await self._audit.record(
            action=action,
            actor=actor,
            resource_type="ops_alert",
            resource_id=int(alert.id),
            after_data={"status": str(alert.status), "note": note},
        )
        await write_operation_log(
            self._session,
            operation=action,
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_alert",
            resource_id=int(alert.id),
        )
        await self._session.commit()

    @staticmethod
    def _as_utc(value: datetime.datetime, *, field: str) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{field} must include a UTC offset")
        return value.astimezone(datetime.UTC)

    @staticmethod
    def _validate_condition(condition: str) -> None:
        if condition not in CONDITION_OPERATORS:
            raise ValidationError(f"condition must be one of {sorted(CONDITION_OPERATORS)}")

    @staticmethod
    def _validate_duration(duration_seconds: int) -> None:
        if int(duration_seconds) < 0:
            raise ValidationError("duration_seconds must not be negative")

    @staticmethod
    def _validate_severity(severity: str) -> None:
        if severity not in ALERT_SEVERITIES:
            raise ValidationError(f"severity must be one of {sorted(ALERT_SEVERITIES)}")

    @staticmethod
    def _validate_scope_type(scope_type: str) -> None:
        if scope_type not in ALERT_SCOPE_TYPES:
            raise ValidationError(f"scope_type must be one of {sorted(ALERT_SCOPE_TYPES)}")

    @staticmethod
    def _to_rule_response(row: OpsAlertRule) -> AlertRuleResponse:
        return AlertRuleResponse(
            id=str(int(row.id)),
            rule_code=str(row.rule_code),
            rule_name=str(row.rule_name),
            alert_type=str(row.alert_type),
            metric_key=str(row.metric_key),
            condition=str(row.condition),
            threshold=float(row.threshold),
            duration_seconds=int(row.duration_seconds),
            severity=str(row.severity),
            scope_type=str(row.scope_type),
            scope_id=str(int(row.scope_id)) if row.scope_id is not None else None,
            notification_policy=row.notification_policy,
            enabled=bool(row.enabled),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_alert_response(row: OpsAlert) -> AlertResponse:
        return AlertResponse(
            id=str(int(row.id)),
            fingerprint=str(row.fingerprint),
            rule_id=str(int(row.rule_id)) if row.rule_id is not None else None,
            alert_type=str(row.alert_type),
            severity=str(row.severity),
            status=str(row.status),
            resource_type=row.resource_type,
            resource_id=str(int(row.resource_id)) if row.resource_id is not None else None,
            host_id=str(int(row.host_id)) if row.host_id is not None else None,
            service_id=str(int(row.service_id)) if row.service_id is not None else None,
            metric_key=row.metric_key,
            metric_value=row.metric_value,
            threshold=row.threshold,
            description=row.description,
            trace_id=row.trace_id,
            triggered_at=row.triggered_at,
            acknowledged_at=row.acknowledged_at,
            acknowledged_by=(
                str(int(row.acknowledged_by)) if row.acknowledged_by is not None else None
            ),
            silenced_until=row.silenced_until,
            silence_reason=row.silence_reason,
            resolved_at=row.resolved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
