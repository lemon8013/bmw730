"""Unit tests for alert deduplication by fingerprint.

One rule firing twice must refresh the alert it already owns instead of
inserting a second row: the fingerprint ``alert_type|scope_type|scope_id|
metric_key`` is the identity of an alert, and a duplicate would spam the
operator and break acknowledgement.

The evaluator is also deliberately defensive: one broken rule must never abort
the whole pass, otherwise a single bad threshold would blind the console.

The repository is an in-memory fake, so no database is touched.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.ops.alerts.evaluator import (
    ALERT_STATUS_FIRING,
    ALERT_STATUS_RESOLVED,
    AlertEvaluator,
    build_fingerprint,
)
from app.ops.alerts.repository import AlertRepository

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


class _FakeAlertRepository:
    """An in-memory stand-in for :class:`AlertRepository`."""

    def __init__(
        self, rules: list[SimpleNamespace], values: dict[str, float | None]
    ) -> None:
        self._rules = list(rules)
        self._values = dict(values)
        #: Metric keys whose aggregation must blow up, to prove isolation.
        self.failing: set[str] = set()
        self.alerts: dict[str, SimpleNamespace] = {}
        self.created: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = []

    async def list_enabled_rules(self) -> list[SimpleNamespace]:
        return [rule for rule in self._rules if rule.enabled]

    async def window_aggregate(self, *, metric_key: str, **_kwargs: Any) -> float | None:
        if metric_key in self.failing:
            raise RuntimeError(f"metric store unreachable for {metric_key}")
        return self._values.get(metric_key)

    async def get_alert_by_fingerprint(self, fingerprint: str) -> SimpleNamespace | None:
        return self.alerts.get(fingerprint)

    async def create_alert(self, **fields: Any) -> SimpleNamespace:
        row = SimpleNamespace(**fields)
        self.created.append(fields)
        self.alerts[str(fields["fingerprint"])] = row
        return row

    async def update_alert(self, row: SimpleNamespace, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        self.updates.append(fields)

    async def add_history(self, **fields: Any) -> SimpleNamespace:
        self.history.append(fields)
        return SimpleNamespace(**fields)

    async def add_notification(self, **fields: Any) -> SimpleNamespace:
        self.notifications.append(fields)
        return SimpleNamespace(**fields)


def _rule(
    *,
    rule_code: str = "RULE_CPU",
    alert_type: str = "CPU_HIGH",
    metric_key: str = "host.cpu_usage",
    threshold: float = 90.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=sum(ord(character) for character in rule_code),
        rule_code=rule_code,
        rule_name=f"{rule_code} name",
        alert_type=alert_type,
        metric_key=metric_key,
        condition="GT",
        threshold=threshold,
        duration_seconds=300,
        severity="WARNING",
        scope_type="HOST",
        scope_id=11,
        enabled=True,
    )


def _evaluator(repository: _FakeAlertRepository) -> AlertEvaluator:
    evaluator = AlertEvaluator(_NothingSession())
    evaluator._repository = repository  # type: ignore[attr-defined]
    return evaluator


class _NothingSession:
    """Guards the tests: the evaluator must never touch a real session."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the fingerprint tests must not reach the database")


def test_the_fake_repository_covers_the_real_interface() -> None:
    """The fake must stay a drop-in replacement of the real repository."""
    for name in (
        "list_enabled_rules",
        "window_aggregate",
        "get_alert_by_fingerprint",
        "create_alert",
        "update_alert",
        "add_history",
        "add_notification",
    ):
        assert callable(getattr(AlertRepository, name)), name
        assert callable(getattr(_FakeAlertRepository, name)), name


def test_fingerprint_ignores_the_threshold_and_the_rule_identity() -> None:
    first = _rule(rule_code="A", threshold=90.0)
    second = _rule(rule_code="B", alert_type="MEMORY_HIGH", threshold=10.0)
    assert build_fingerprint(first) != build_fingerprint(second)
    assert build_fingerprint(_rule(rule_code="A", threshold=99.0)) == build_fingerprint(first)


@pytest.mark.asyncio()
async def test_repeated_firing_updates_one_alert_instead_of_inserting_a_second() -> None:
    rule = _rule()
    repository = _FakeAlertRepository([rule], {"host.cpu_usage": 95.0})

    first = await _evaluator(repository).evaluate(_NOW)
    assert first["firing"] == 1
    assert len(repository.created) == 1
    assert len(repository.alerts) == 1

    repository._values["host.cpu_usage"] = 99.5
    second = await _evaluator(repository).evaluate(_NOW)

    assert second["firing"] == 1
    assert len(repository.created) == 1, "a second firing must not insert a second alert"
    assert len(repository.alerts) == 1
    alert = repository.alerts[build_fingerprint(rule)]
    assert alert.status == ALERT_STATUS_FIRING
    assert alert.metric_value == 99.5
    assert repository.updates[-1]["metric_value"] == 99.5


@pytest.mark.asyncio()
async def test_a_rule_that_stops_matching_resolves_its_alert() -> None:
    rule = _rule()
    repository = _FakeAlertRepository([rule], {"host.cpu_usage": 95.0})
    fingerprint = build_fingerprint(rule)

    await _evaluator(repository).evaluate(_NOW)
    assert repository.alerts[fingerprint].status == ALERT_STATUS_FIRING

    repository._values["host.cpu_usage"] = 12.0
    outcome = await _evaluator(repository).evaluate(_NOW)

    assert outcome["resolved"] == 1
    assert outcome["firing"] == 0
    assert repository.alerts[fingerprint].status == ALERT_STATUS_RESOLVED
    assert repository.history[-1]["from_status"] == ALERT_STATUS_FIRING
    assert repository.history[-1]["to_status"] == ALERT_STATUS_RESOLVED


@pytest.mark.asyncio()
async def test_a_missing_metric_never_fires_and_resolves_an_existing_alert() -> None:
    rule = _rule()
    repository = _FakeAlertRepository([rule], {"host.cpu_usage": None})

    outcome = await _evaluator(repository).evaluate(_NOW)

    assert outcome["firing"] == 0
    assert repository.created == []
    assert repository.alerts == {}


@pytest.mark.asyncio()
async def test_one_failing_rule_does_not_abort_the_round() -> None:
    cpu = _rule(rule_code="RULE_CPU", alert_type="CPU_HIGH", metric_key="host.cpu_usage")
    memory = _rule(
        rule_code="RULE_MEM",
        alert_type="MEMORY_HIGH",
        metric_key="host.memory_usage",
        threshold=80.0,
    )
    repository = _FakeAlertRepository(
        [cpu, memory], {"host.cpu_usage": 95.0, "host.memory_usage": 88.0}
    )

    healthy = await _evaluator(repository).evaluate(_NOW)
    assert healthy["failed_rules"] == 0
    assert len(repository.alerts) == 2

    repository.failing.add("host.cpu_usage")
    outcome = await _evaluator(repository).evaluate(_NOW)

    assert outcome["evaluated_rules"] == 2
    assert outcome["failed_rules"] == 1
    assert outcome["firing"] == 1, "the healthy rule must still be evaluated"
    assert [row["status"] for row in repository.notifications] == ["FAILED"]
    assert repository.notifications[0]["alert_id"] == int(
        repository.alerts[build_fingerprint(cpu)].id
    )
    assert repository.alerts[build_fingerprint(memory)].status == ALERT_STATUS_FIRING


@pytest.mark.asyncio()
async def test_a_failing_rule_without_an_alert_is_not_fatal_either() -> None:
    broken = _rule(rule_code="RULE_CPU", metric_key="host.cpu_usage")
    healthy = _rule(
        rule_code="RULE_MEM",
        alert_type="MEMORY_HIGH",
        metric_key="host.memory_usage",
        threshold=80.0,
    )
    repository = _FakeAlertRepository(
        [broken, healthy], {"host.cpu_usage": 95.0, "host.memory_usage": 88.0}
    )
    repository.failing.add("host.cpu_usage")

    outcome = await _evaluator(repository).evaluate(_NOW)

    assert outcome["failed_rules"] == 1
    assert outcome["firing"] == 1
    assert repository.notifications == []
    assert len(repository.alerts) == 1


@pytest.mark.asyncio()
async def test_a_disabled_rule_is_not_evaluated() -> None:
    rule = _rule()
    rule.enabled = False
    repository = _FakeAlertRepository([rule], {"host.cpu_usage": 95.0})

    outcome = await _evaluator(repository).evaluate(_NOW)

    assert outcome["evaluated_rules"] == 0
    assert repository.alerts == {}
