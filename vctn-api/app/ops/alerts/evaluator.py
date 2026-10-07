"""app.ops.alerts — threshold evaluation (OPS-DECISION-008).

The evaluator is deliberately defensive: one broken rule or one unreachable
metric table must never abort the run, so every rule is evaluated in isolation
and a failure is recorded as a ``FAILED`` notification row for the alert that
the rule addresses (or logged when no alert exists yet).
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ops.alerts.model import OpsAlert, OpsAlertRule
from app.ops.alerts.repository import AlertRepository
from app.ops.notifications.dispatcher import NotificationDispatcher
from app.shared.ids import new_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.shared.auth.context import Principal

_LOGGER = get_logger(__name__)

ALERT_STATUS_TRIGGERED: str = "TRIGGERED"
ALERT_STATUS_FIRING: str = "FIRING"
ALERT_STATUS_ACKNOWLEDGED: str = "ACKNOWLEDGED"
ALERT_STATUS_RESOLVED: str = "RESOLVED"

ALERT_STATUSES: frozenset[str] = frozenset(
    {
        ALERT_STATUS_TRIGGERED,
        ALERT_STATUS_FIRING,
        ALERT_STATUS_ACKNOWLEDGED,
        ALERT_STATUS_RESOLVED,
    }
)

ALERT_SEVERITIES: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})
ALERT_SCOPE_TYPES: frozenset[str] = frozenset({"GLOBAL", "HOST", "SERVICE", "ENDPOINT"})

#: Condition operators supported by the rule engine.
CONDITION_OPERATORS: frozenset[str] = frozenset({"GT", "GTE", "LT", "LTE", "EQ", "NE"})

_MAX_FINGERPRINT_LENGTH: int = 128


def build_fingerprint(rule: OpsAlertRule) -> str:
    """Return the stable deduplication key of the alert a rule addresses."""
    scope_id = "" if rule.scope_id is None else str(int(rule.scope_id))
    return (
        f"{rule.alert_type}|{rule.scope_type}|{scope_id}|{rule.metric_key}"
    )[:_MAX_FINGERPRINT_LENGTH]


def matches_condition(*, condition: str, value: float, threshold: float) -> bool:
    """Evaluate one condition against an aggregated metric value."""
    if condition in {"GT", "GTE", "LT", "LTE"}:
        # 浮点阈值来自 DB，1e-9 的容差避免等值边界反复抖动。
        tolerance = 1e-9
        if condition == "GT":
            return value - threshold > tolerance
        if condition == "GTE":
            return value - threshold > -tolerance
        if condition == "LT":
            return value - threshold < -tolerance
        return value - threshold < tolerance
    if condition == "EQ":
        return abs(value - threshold) <= 1e-9
    if condition == "NE":
        return abs(value - threshold) > 1e-9
    raise ValueError(f"unsupported condition: {condition}")


def _scope_filters(rule: OpsAlertRule) -> dict[str, int | None]:
    scope_id = int(rule.scope_id) if rule.scope_id is not None else None
    return {
        "host_id": scope_id if rule.scope_type == "HOST" else None,
        "service_id": scope_id if rule.scope_type == "SERVICE" else None,
        "endpoint_id": scope_id if rule.scope_type == "ENDPOINT" else None,
    }


def _resource_type(rule: OpsAlertRule) -> str | None:
    return None if rule.scope_type == "GLOBAL" else rule.scope_type


def _describe(rule: OpsAlertRule, value: float) -> str:
    return (
        f"{rule.rule_name}: {rule.metric_key} {rule.condition} {rule.threshold} "
        f"(observed {round(value, 6)})"
    )


class AlertEvaluator:
    """Evaluates every enabled rule against the metric store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = AlertRepository(session)
        # Built on first use: construction must stay free of side effects, and a
        # pass without a notification policy must never build a dispatcher.
        self._notification_dispatcher: NotificationDispatcher | None = None

    async def evaluate(self, now: datetime.datetime) -> dict[str, int]:
        """Run one evaluation pass and return per-outcome counters.

        The counters only describe what this pass did; they are not a business
        rule. No exception ever leaves this method.
        """
        outcome = {"evaluated_rules": 0, "firing": 0, "resolved": 0, "failed_rules": 0}
        rules = await self._repository.list_enabled_rules()
        outcome["evaluated_rules"] = len(rules)
        for rule in rules:
            try:
                hit = await self._evaluate_rule(rule, now)
            except Exception as exc:  # noqa: BLE001 - 一条规则失败不能中断整轮评估
                outcome["failed_rules"] += 1
                await self._record_rule_failure(rule, exc)
                continue
            if hit:
                outcome["firing"] += 1
            else:
                outcome["resolved"] += 1
        return outcome

    async def _evaluate_rule(self, rule: OpsAlertRule, now: datetime.datetime) -> bool:
        """Evaluate one rule and return ``True`` when it stays firing."""
        if rule.duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative")
        start = now - datetime.timedelta(seconds=int(rule.duration_seconds or 0))
        value = await self._repository.window_aggregate(
            metric_key=str(rule.metric_key),
            start=start,
            end=now,
            **_scope_filters(rule),
        )
        hit = value is not None and matches_condition(
            condition=str(rule.condition),
            value=value,
            threshold=float(rule.threshold),
        )
        if hit and value is not None:
            await self._fire(rule, value, now)
        else:
            await self._resolve(rule, now)
        return hit

    async def _fire(self, rule: OpsAlertRule, value: float, now: datetime.datetime) -> None:
        fingerprint = build_fingerprint(rule)
        alert = await self._repository.get_alert_by_fingerprint(fingerprint)
        scope_id = int(rule.scope_id) if rule.scope_id is not None else None
        host_id = scope_id if rule.scope_type == "HOST" else None
        service_id = scope_id if rule.scope_type == "SERVICE" else None
        if alert is None:
            alert = await self._repository.create_alert(
                id=new_id(),
                fingerprint=fingerprint,
                rule_id=int(rule.id),
                alert_type=str(rule.alert_type),
                severity=str(rule.severity),
                status=ALERT_STATUS_FIRING,
                resource_type=_resource_type(rule),
                resource_id=scope_id,
                host_id=host_id,
                service_id=service_id,
                metric_key=str(rule.metric_key),
                metric_value=value,
                threshold=float(rule.threshold),
                description=_describe(rule, value),
                triggered_at=now,
                created_at=now,
                updated_at=now,
            )
            await self._notify(rule, alert, now)
            return
        # 指纹已存在：只刷新观测值，绝不重复插入一条告警。
        # 只有一条已恢复的告警重新命中才算"再次触发"，重新发一次通知；
        # 仍在 FIRING / ACKNOWLEDGED 的告警每轮都发会把渠道刷爆。
        retriggered = str(alert.status) == ALERT_STATUS_RESOLVED
        await self._repository.update_alert(
            alert,
            metric_value=value,
            threshold=float(rule.threshold),
            description=_describe(rule, value),
            severity=str(rule.severity),
            rule_id=int(rule.id),
            updated_at=now,
        )
        if retriggered:
            await self._transition(
                alert,
                ALERT_STATUS_FIRING,
                now,
                actor=None,
                note="re-triggered by rule evaluation",
            )
            await self._notify(rule, alert, now)

    async def _notify(
        self,
        rule: OpsAlertRule,
        alert: OpsAlert,
        now: datetime.datetime,
    ) -> None:
        """Deliver the alert through the channels its rule names.

        Notification is a side effect of the alert, never a precondition: a
        delivery problem is logged and the evaluation counters stay as they are.
        """
        try:
            await self._dispatcher().dispatch(alert, rule, now)
        except Exception as exc:  # noqa: BLE001 - 通知失败不能影响本轮评估结果
            _LOGGER.warning(
                "alert notification dispatch failed rule_code=%s error=%s",
                rule.rule_code,
                f"{type(exc).__name__}: {exc}",
            )

    def _dispatcher(self) -> NotificationDispatcher:
        if self._notification_dispatcher is None:
            self._notification_dispatcher = NotificationDispatcher(self._session)
        return self._notification_dispatcher

    async def _resolve(self, rule: OpsAlertRule, now: datetime.datetime) -> None:
        fingerprint = build_fingerprint(rule)
        alert = await self._repository.get_alert_by_fingerprint(fingerprint)
        if alert is None or alert.status != ALERT_STATUS_FIRING:
            return
        await self._transition(alert, ALERT_STATUS_RESOLVED, now, actor=None, note=None)

    async def _record_rule_failure(self, rule: OpsAlertRule, exc: BaseException) -> None:
        fingerprint = build_fingerprint(rule)
        alert = await self._repository.get_alert_by_fingerprint(fingerprint)
        message = f"{type(exc).__name__}: {exc}"
        if alert is None:
            _LOGGER.warning(
                "alert rule evaluation failed rule_code=%s error=%s",
                rule.rule_code,
                message,
            )
            return
        await self._repository.add_notification(
            id=new_id(),
            alert_id=int(alert.id),
            channel_id=None,
            channel_code="EVALUATOR",
            receiver=None,
            status="FAILED",
            retry_count=0,
            sent_at=None,
            error_message=message[:1000],
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC),
        )

    async def _transition(
        self,
        alert: OpsAlert,
        to_status: str,
        now: datetime.datetime,
        *,
        actor: Principal | None,
        note: str | None,
    ) -> None:
        from_status = str(alert.status)
        await self._repository.update_alert(alert, status=to_status, updated_at=now)
        await self._repository.add_history(
            id=new_id(),
            alert_id=int(alert.id),
            from_status=from_status,
            to_status=to_status,
            actor_id=actor.subject_id if actor is not None else None,
            actor_username=actor.username if actor is not None else None,
            note=note,
            created_at=now,
        )
