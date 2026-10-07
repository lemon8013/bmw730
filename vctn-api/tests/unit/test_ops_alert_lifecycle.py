"""Unit tests for the alert lifecycle: ack, silence and resolve.

The service owns the transaction, so every transition must write a history row,
an audit record and an operation log and then commit exactly once. The two rules
that matter most:

* silencing is a *separate dimension* — it suppresses notification only and
  must never move the alert out of ``FIRING``;
* resolving is only allowed once the alert is acknowledged (or its rule no
  longer matches), because setting ``RESOLVED`` on a firing alert would forge a
  recovery.

The repositories are stubbed, so no database is touched.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.admin.audit.model import SysOperationLog
from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, ConflictError, ValidationError
from app.ops.alerts.evaluator import (
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_FIRING,
    ALERT_STATUS_RESOLVED,
    ALERT_STATUS_TRIGGERED,
)
from app.ops.alerts.schema import (
    AlertAckRequest,
    AlertResolveRequest,
    AlertSilenceRequest,
)
from app.ops.alerts.service import AlertService
from app.shared.auth.context import Principal

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)

#: The aggregated metric value the stub reports; it is above the 90.0 threshold
#: of :func:`_rule`, so the rule still matches and "resolve" stays guarded.
_STILL_FIRING_VALUE = 95.0


class _FakeSession:
    """A session that records what the service appended and committed."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0
        self.flushes = 0

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the alert lifecycle tests must not reach the database")

    def operations(self) -> list[str]:
        return [row.operation for row in self.added if isinstance(row, SysOperationLog)]


class _RecordingAudit:
    """Stands in for :class:`OpsAuditRecorder` and records every action."""

    def __init__(self) -> None:
        self.actions: list[str] = []
        self.payloads: list[dict[str, Any]] = []

    async def record(self, *, action: str, **kwargs: Any) -> None:
        self.actions.append(action)
        self.payloads.append(kwargs)


class _StubAlertRepository:
    """The alert reads and writes the lifecycle touches, in memory."""

    def __init__(
        self,
        alert: SimpleNamespace,
        *,
        rule: SimpleNamespace | None,
        aggregate: float | None,
    ) -> None:
        self._alert = alert
        self._rule = rule
        self._aggregate = aggregate
        self.updates: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.aggregate_calls: list[dict[str, Any]] = []

    async def get_alert(self, alert_id: int) -> SimpleNamespace | None:
        return self._alert if alert_id == int(self._alert.id) else None

    async def get_rule(self, rule_id: int) -> SimpleNamespace | None:
        return self._rule

    async def window_aggregate(self, **kwargs: Any) -> float | None:
        self.aggregate_calls.append(kwargs)
        return self._aggregate

    async def update_alert(self, row: SimpleNamespace, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        self.updates.append(fields)

    async def add_history(self, **fields: Any) -> SimpleNamespace:
        self.history.append(fields)
        return SimpleNamespace(**fields)


def _actor() -> Principal:
    return Principal(
        subject_id=7,
        subject_type="admin",
        session_id=1,
        username="ops-admin",
        display_name="ops admin",
    )


def _rule() -> SimpleNamespace:
    return SimpleNamespace(
        id=900,
        enabled=True,
        metric_key="host.cpu_usage",
        condition="GT",
        threshold=90.0,
        duration_seconds=300,
    )


def _alert(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "id": 5001,
        "fingerprint": "CPU_HIGH|HOST|11|host.cpu_usage",
        "rule_id": 900,
        "alert_type": "CPU_HIGH",
        "severity": "WARNING",
        "status": ALERT_STATUS_TRIGGERED,
        "resource_type": "HOST",
        "resource_id": 11,
        "host_id": 11,
        "service_id": None,
        "metric_key": "host.cpu_usage",
        "metric_value": _STILL_FIRING_VALUE,
        "threshold": 90.0,
        "description": "cpu is high",
        "trace_id": None,
        "triggered_at": _NOW,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "silenced_until": None,
        "silence_reason": None,
        "resolved_at": None,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _service(
    alert: SimpleNamespace,
    *,
    rule: SimpleNamespace | None = None,
    aggregate: float | None = _STILL_FIRING_VALUE,
) -> tuple[AlertService, _StubAlertRepository, _FakeSession, _RecordingAudit]:
    session = _FakeSession()
    service = AlertService(session, Settings(_env_file=None))
    repository = _StubAlertRepository(
        alert, rule=_rule() if rule is None else rule, aggregate=aggregate
    )
    audit = _RecordingAudit()
    service._repository = repository  # type: ignore[attr-defined]
    service._audit = audit  # type: ignore[attr-defined]
    return service, repository, session, audit


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "from_status", [ALERT_STATUS_TRIGGERED, ALERT_STATUS_FIRING], ids=("triggered", "firing")
)
async def test_ack_moves_an_open_alert_to_acknowledged(from_status: str) -> None:
    alert = _alert(status=from_status)
    service, repository, session, audit = _service(alert)

    response = await service.acknowledge_alert(
        _actor(), 5001, AlertAckRequest(note="taking over")
    )

    assert response.status == ALERT_STATUS_ACKNOWLEDGED
    assert alert.status == ALERT_STATUS_ACKNOWLEDGED
    assert alert.acknowledged_by == 7
    assert alert.acknowledged_at is not None
    assert [row["from_status"] for row in repository.history] == [from_status]
    assert [row["to_status"] for row in repository.history] == [ALERT_STATUS_ACKNOWLEDGED]
    assert repository.history[0]["note"] == "taking over"
    assert audit.actions == ["OPS_ALERT_ACK"]
    assert session.operations() == ["OPS_ALERT_ACK"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_ack_of_an_already_acknowledged_alert_is_refused() -> None:
    alert = _alert(status=ALERT_STATUS_ACKNOWLEDGED)
    service, repository, _session, audit = _service(alert)

    with pytest.raises(ConflictError):
        await service.acknowledge_alert(_actor(), 5001, AlertAckRequest())

    assert alert.status == ALERT_STATUS_ACKNOWLEDGED
    assert repository.history == []
    assert audit.actions == []


@pytest.mark.asyncio()
async def test_silence_only_writes_silenced_until_and_keeps_the_status() -> None:
    alert = _alert(status=ALERT_STATUS_FIRING)
    service, repository, session, audit = _service(alert)

    response = await service.silence_alert(
        _actor(), 5001, AlertSilenceRequest(silence_minutes=30, silence_reason="planned work")
    )

    assert response.status == ALERT_STATUS_FIRING
    assert alert.status == ALERT_STATUS_FIRING
    assert response.silenced_until is not None
    assert alert.silenced_until is not None
    assert alert.silenced_until > datetime.datetime.now(datetime.UTC)
    assert alert.silence_reason == "planned work"
    # Silencing must not be mistaken for an acknowledgement or a recovery.
    assert alert.acknowledged_at is None
    assert alert.resolved_at is None
    assert all("status" not in row for row in repository.updates)
    assert repository.history[0]["from_status"] == ALERT_STATUS_FIRING
    assert repository.history[0]["to_status"] == ALERT_STATUS_FIRING
    assert audit.actions == ["OPS_ALERT_SILENCE"]
    assert session.operations() == ["OPS_ALERT_SILENCE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_silence_refuses_a_non_positive_window() -> None:
    alert = _alert(status=ALERT_STATUS_FIRING)
    service, repository, _session, audit = _service(alert)

    with pytest.raises(ValidationError):
        await service.silence_alert(
            _actor(), 5001, AlertSilenceRequest(silence_minutes=0, silence_reason="nope")
        )

    assert alert.silenced_until is None
    assert repository.history == []
    assert audit.actions == []


@pytest.mark.asyncio()
async def test_resolve_is_refused_while_the_alert_is_unacknowledged() -> None:
    """A rule that still matches plus no acknowledgement: forging a recovery."""
    alert = _alert(status=ALERT_STATUS_TRIGGERED)
    service, repository, session, audit = _service(alert, aggregate=_STILL_FIRING_VALUE)

    with pytest.raises(BusinessRuleError):
        await service.resolve_alert(_actor(), 5001, AlertResolveRequest(note="looks fine"))

    assert alert.status == ALERT_STATUS_TRIGGERED
    assert alert.resolved_at is None
    assert repository.history == []
    assert audit.actions == []
    assert session.commits == 0
    # The rule was actually consulted, so the refusal is not accidental.
    assert repository.aggregate_calls


@pytest.mark.asyncio()
async def test_resolve_is_allowed_once_the_alert_is_acknowledged() -> None:
    """An acknowledged alert may be resolved even while the rule still fires."""
    alert = _alert(status=ALERT_STATUS_ACKNOWLEDGED)
    service, repository, session, audit = _service(alert, aggregate=_STILL_FIRING_VALUE)

    response = await service.resolve_alert(_actor(), 5001, AlertResolveRequest(note="fixed"))

    assert response.status == ALERT_STATUS_RESOLVED
    assert alert.status == ALERT_STATUS_RESOLVED
    assert alert.resolved_at is not None
    assert repository.history[0]["from_status"] == ALERT_STATUS_ACKNOWLEDGED
    assert repository.history[0]["to_status"] == ALERT_STATUS_RESOLVED
    assert repository.history[0]["note"] == "fixed"
    assert audit.actions == ["OPS_ALERT_RESOLVE"]
    assert session.operations() == ["OPS_ALERT_RESOLVE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_resolve_is_allowed_when_the_rule_no_longer_matches() -> None:
    """A cleared alert may be resolved without an acknowledgement."""
    alert = _alert(status=ALERT_STATUS_TRIGGERED)
    service, repository, session, audit = _service(alert, aggregate=10.0)

    response = await service.resolve_alert(_actor(), 5001, AlertResolveRequest())

    assert response.status == ALERT_STATUS_RESOLVED
    assert alert.resolved_at is not None
    assert repository.history[0]["to_status"] == ALERT_STATUS_RESOLVED
    assert audit.actions == ["OPS_ALERT_RESOLVE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_resolve_of_an_alert_without_a_rule_is_allowed() -> None:
    """A manual alert has no rule to re-check, so it must not be blocked."""
    alert = _alert(status=ALERT_STATUS_TRIGGERED, rule_id=None)
    service, repository, session, _audit = _service(alert)

    response = await service.resolve_alert(_actor(), 5001, AlertResolveRequest())

    assert response.status == ALERT_STATUS_RESOLVED
    assert repository.aggregate_calls == []
    assert session.commits == 1
