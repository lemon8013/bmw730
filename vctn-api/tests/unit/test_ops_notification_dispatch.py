"""Unit tests for the alert to notification dispatch chain.

The chain is the only way an alert reaches a channel, so these tests pin the
behaviour that matters to an operator:

* a rule that names no channel notifies nobody and touches no database at all;
* a missing or disabled channel is a ``FAILED`` row, never a silent drop;
* a silenced alert and a maintenance window both produce ``SKIPPED``, and a
  ``SKIPPED`` row keeps the channel it would have used;
* a provider that raises is a ``FAILED`` row and never fails the dispatch.

Everything is stubbed, so no database and no network is touched.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.ops.notifications.dispatcher import (
    NotificationDispatcher,
    resolve_channel_codes,
    resolve_group_codes,
)
from app.ops.notifications.providers import (
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_STATUS_SKIPPED,
    NotificationChannel,
    NotificationRegistry,
    NotificationResult,
)

_NOW = datetime.datetime(2026, 8, 1, 10, 0, tzinfo=datetime.UTC)


class _FakeSession:
    """Guards the tests: the dispatcher must not reach a session directly."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the dispatch tests must not reach the database")


class _StubAlertRepository:
    def __init__(self) -> None:
        self.notifications: list[dict[str, Any]] = []

    async def add_notification(self, **fields: Any) -> SimpleNamespace:
        self.notifications.append(fields)
        return SimpleNamespace(**fields)


class _StubNotificationRepository:
    def __init__(
        self,
        channels: dict[str, SimpleNamespace],
        groups: dict[str, SimpleNamespace] | None = None,
    ) -> None:
        self._channels = dict(channels)
        self._groups = dict(groups or {})
        self.group_lookups: list[tuple[str, ...]] = []

    async def get_channel_by_code(self, channel_code: str) -> SimpleNamespace | None:
        return self._channels.get(channel_code)

    async def list_groups_by_codes(self, group_codes: Any) -> list[SimpleNamespace]:
        self.group_lookups.append(tuple(group_codes))
        return [self._groups[code] for code in group_codes if code in self._groups]


class _StubMaintenanceRepository:
    def __init__(self, window: SimpleNamespace | None = None) -> None:
        self._window = window
        self.calls: list[dict[str, Any]] = []

    async def find_suppressing(
        self,
        *,
        at: datetime.datetime,
        scope_type: str | None = None,
        scope_id: int | None = None,
    ) -> SimpleNamespace | None:
        self.calls.append({"at": at, "scope_type": scope_type, "scope_id": scope_id})
        return self._window


class _FakeProvider(NotificationChannel):
    """Records what it was asked to send and returns a canned result."""

    def __init__(self, result: NotificationResult | None = None) -> None:
        self._result = result or NotificationResult(
            status=NOTIFICATION_STATUS_SENT, receiver="https://hooks.test/ops"
        )
        self.sent: list[tuple[Any, Any]] = []

    @property
    def channel_type(self) -> str:
        return "WEBHOOK"

    async def send(self, alert: Any, channel: Any) -> NotificationResult:
        self.sent.append((alert, channel))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _channel(
    *,
    code: str = "CH_WEBHOOK",
    channel_type: str = "WEBHOOK",
    enabled: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=3101,
        channel_code=code,
        channel_type=channel_type,
        enabled=enabled,
        config={"url": "https://hooks.test/ops"},
    )


def _rule(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "id": 900,
        "rule_code": "RULE_CPU",
        "alert_type": "CPU_HIGH",
        "metric_key": "host.cpu_usage",
        "condition": "GT",
        "threshold": 90.0,
        "scope_type": "HOST",
        "scope_id": 11,
        "enabled": True,
        "notification_policy": {"channel_codes": ["CH_WEBHOOK"]},
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _alert(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "id": 5001,
        "fingerprint": "CPU_HIGH|HOST|11|host.cpu_usage",
        "rule_id": 900,
        "alert_type": "CPU_HIGH",
        "severity": "WARNING",
        "status": "FIRING",
        "resource_type": "HOST",
        "resource_id": 11,
        "host_id": 11,
        "service_id": None,
        "metric_key": "host.cpu_usage",
        "metric_value": 95.0,
        "threshold": 90.0,
        "description": "cpu is high",
        "triggered_at": _NOW,
        "silenced_until": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _dispatcher(
    *,
    channels: dict[str, SimpleNamespace] | None = None,
    groups: dict[str, SimpleNamespace] | None = None,
    window: SimpleNamespace | None = None,
    provider: _FakeProvider | None = None,
) -> tuple[NotificationDispatcher, _StubAlertRepository, _StubMaintenanceRepository, _FakeProvider]:
    used_provider = provider or _FakeProvider()
    dispatcher = NotificationDispatcher(
        _FakeSession(),  # type: ignore[arg-type]
        registry=NotificationRegistry({"WEBHOOK": used_provider}),
    )
    alerts = _StubAlertRepository()
    maintenance = _StubMaintenanceRepository(window)
    dispatcher._alerts = alerts  # type: ignore[attr-defined]
    dispatcher._channels = _StubNotificationRepository(  # type: ignore[attr-defined]
        channels if channels is not None else {"CH_WEBHOOK": _channel()}, groups
    )
    dispatcher._maintenance = maintenance  # type: ignore[attr-defined]
    return dispatcher, alerts, maintenance, used_provider


def test_policy_resolution_accepts_both_key_aliases_and_deduplicates() -> None:
    assert resolve_channel_codes({"channel_codes": ["A", "B", "A"]}) == ("A", "B")
    assert resolve_channel_codes({"channels": "SOLO"}) == ("SOLO",)
    assert resolve_channel_codes(None) == ()
    # A policy value that is neither a string nor a list yields nothing.
    assert resolve_channel_codes({"channel_codes": 42}) == ()
    assert resolve_channel_codes({"channel_codes": ["  ", "A"]}) == ("A",)
    assert resolve_group_codes({"group_codes": ["G1"]}) == ("G1",)
    assert resolve_group_codes({"groups": []}) == ()


@pytest.mark.asyncio()
async def test_a_rule_without_a_policy_notifies_nobody() -> None:
    """No policy means no channel: not even a read must happen."""
    dispatcher, alerts, maintenance, provider = _dispatcher()
    rule = _rule(notification_policy=None)

    records = await dispatcher.dispatch(_alert(), rule, _NOW)

    assert records == []
    assert alerts.notifications == []
    assert maintenance.calls == []
    assert provider.sent == []


@pytest.mark.asyncio()
async def test_a_healthy_channel_is_sent_and_recorded() -> None:
    dispatcher, alerts, _maintenance, provider = _dispatcher()

    records = await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert len(records) == 1
    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_SENT
    assert alerts.notifications[0]["channel_code"] == "CH_WEBHOOK"
    assert alerts.notifications[0]["channel_id"] == 3101
    assert alerts.notifications[0]["sent_at"] == _NOW
    assert alerts.notifications[0]["error_message"] is None
    assert len(provider.sent) == 1


@pytest.mark.asyncio()
async def test_a_missing_channel_is_a_failure_not_a_silence() -> None:
    dispatcher, alerts, _maintenance, provider = _dispatcher(channels={})

    await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert [row["status"] for row in alerts.notifications] == [NOTIFICATION_STATUS_FAILED]
    assert "missing or disabled" in str(alerts.notifications[0]["error_message"])
    # A channel that does not exist cannot be referenced: no dangling FK.
    assert alerts.notifications[0]["channel_id"] is None
    assert provider.sent == []


@pytest.mark.asyncio()
async def test_a_disabled_channel_is_a_failure_too() -> None:
    dispatcher, alerts, _maintenance, provider = _dispatcher(
        channels={"CH_WEBHOOK": _channel(enabled=False)}
    )

    await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_FAILED
    assert provider.sent == []


@pytest.mark.asyncio()
async def test_an_unsupported_channel_type_is_a_failure() -> None:
    dispatcher, alerts, _maintenance, provider = _dispatcher(
        channels={"CH_WEBHOOK": _channel(channel_type="SMS")}
    )

    await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_FAILED
    assert "no provider" in str(alerts.notifications[0]["error_message"])
    assert provider.sent == []


@pytest.mark.asyncio()
async def test_a_silenced_alert_is_skipped_and_keeps_its_channel() -> None:
    dispatcher, alerts, _maintenance, provider = _dispatcher()
    alert = _alert(silenced_until=_NOW + datetime.timedelta(minutes=30))

    await dispatcher.dispatch(alert, _rule(), _NOW)

    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_SKIPPED
    assert alerts.notifications[0]["channel_id"] == 3101
    assert "silenced" in str(alerts.notifications[0]["error_message"])
    assert alerts.notifications[0]["sent_at"] is None
    assert provider.sent == []


@pytest.mark.asyncio()
async def test_an_expired_silence_does_not_skip() -> None:
    dispatcher, alerts, _maintenance, _provider = _dispatcher()
    alert = _alert(silenced_until=_NOW - datetime.timedelta(minutes=1))

    await dispatcher.dispatch(alert, _rule(), _NOW)

    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_SENT


@pytest.mark.asyncio()
async def test_a_maintenance_window_suppresses_the_dispatch() -> None:
    window = SimpleNamespace(
        id=7001, window_code="WIN_NIGHTLY", scope_type="GLOBAL", scope_id=None
    )
    dispatcher, alerts, maintenance, provider = _dispatcher(window=window)

    await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_SKIPPED
    assert "WIN_NIGHTLY" in str(alerts.notifications[0]["error_message"])
    assert provider.sent == []
    # The window is matched against the rule scope, not against a global sweep.
    assert maintenance.calls[0]["scope_type"] == "HOST"
    assert maintenance.calls[0]["scope_id"] == 11
    assert maintenance.calls[0]["at"] == _NOW


@pytest.mark.asyncio()
async def test_a_provider_that_raises_is_a_failed_row_not_a_crash() -> None:
    dispatcher, alerts, _maintenance, _provider = _dispatcher(
        provider=_FakeProvider(RuntimeError("boom"))
    )

    records = await dispatcher.dispatch(_alert(), _rule(), _NOW)

    assert len(records) == 1
    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_FAILED
    assert "RuntimeError: boom" in str(alerts.notifications[0]["error_message"])


@pytest.mark.asyncio()
async def test_group_codes_are_expanded_into_their_channels() -> None:
    group = SimpleNamespace(
        id=3201, group_code="G_OPS", channel_codes=["CH_A", "CH_B"], enabled=True
    )
    channels = {
        "CH_A": _channel(code="CH_A"),
        "CH_B": _channel(code="CH_B", enabled=False),
    }
    dispatcher, alerts, _maintenance, _provider = _dispatcher(
        channels=channels, groups={"G_OPS": group}
    )
    rule = _rule(notification_policy={"group_codes": ["G_OPS"]})

    await dispatcher.dispatch(_alert(), rule, _NOW)

    assert sorted(row["channel_code"] for row in alerts.notifications) == ["CH_A", "CH_B"]
    assert [row["status"] for row in alerts.notifications] == [
        NOTIFICATION_STATUS_SENT,
        NOTIFICATION_STATUS_FAILED,
    ]


@pytest.mark.asyncio()
async def test_one_broken_channel_does_not_stop_the_others() -> None:
    channels = {"CH_A": _channel(code="CH_A"), "CH_B": _channel(code="CH_B")}
    dispatcher, alerts, _maintenance, _provider = _dispatcher(channels=channels)
    rule = _rule(notification_policy={"channel_codes": ["CH_A", "CH_B"]})
    # The repository blows up for the second code: a FAILED row must still land.
    original = dispatcher._channels.get_channel_by_code  # type: ignore[attr-defined]

    async def flaky(code: str) -> SimpleNamespace | None:
        if code == "CH_B":
            raise RuntimeError("channel store unreachable")
        return await original(code)

    dispatcher._channels.get_channel_by_code = flaky  # type: ignore[attr-defined]

    await dispatcher.dispatch(_alert(), rule, _NOW)

    assert [row["channel_code"] for row in alerts.notifications] == ["CH_A", "CH_B"]
    assert alerts.notifications[0]["status"] == NOTIFICATION_STATUS_SENT
    assert alerts.notifications[1]["status"] == NOTIFICATION_STATUS_FAILED
