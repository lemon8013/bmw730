"""app.ops.notifications — alert to channel dispatch (OPS-DECISION-009).

This is the only place where an alert becomes an outbound message. The chain is
deliberately narrow and every step leaves a row in ``ops_alert_notification``:

``PENDING -> SENT``
    the provider delivered it;
``-> FAILED``
    the channel is missing, disabled, of an unknown type, or the provider
    reported an error;
``-> SKIPPED``
    the alert is silenced, or a maintenance window covers its scope.

Two properties matter more than throughput here:

* **A rule without a notification policy notifies nobody.** Resolving the
  policy is the first step and it is pure: when it yields no channel code the
  dispatcher returns before touching the database, so an unconfigured rule can
  never broadcast and can never slow down an evaluation pass.
* **One broken channel cannot break an evaluation pass.** Every channel is
  dispatched in isolation and a provider is not allowed to raise; a raise that
  still escapes is caught and recorded as ``FAILED``.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.ops.alerts.repository import AlertRepository
from app.ops.maintenance.repository import MaintenanceRepository
from app.ops.notifications.model import OpsNotificationChannel
from app.ops.notifications.providers import (
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_STATUS_SKIPPED,
    NotificationChannel,
    NotificationRegistry,
    NotificationResult,
    UnsupportedChannelError,
    build_default_registry,
)
from app.ops.notifications.repository import NotificationRepository
from app.shared.ids import new_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.ops.alerts.model import OpsAlert, OpsAlertNotification, OpsAlertRule

_LOGGER = get_logger(__name__)

#: Keys a rule may use to name its channels. ``channels`` is the short alias.
POLICY_CHANNEL_KEYS: tuple[str, ...] = ("channel_codes", "channels")
#: Keys a rule may use to name notification groups that carry channel codes.
POLICY_GROUP_KEYS: tuple[str, ...] = ("group_codes", "groups")

_MAX_ERROR_MESSAGE_LENGTH: int = 1000


def resolve_channel_codes(policy: object) -> tuple[str, ...]:
    """Return the distinct channel codes named by ``policy``.

    Only ``channel_codes``/``channels`` are direct. Group codes need a database
    read to be expanded, so :meth:`NotificationDispatcher.expand_codes` does
    that, and this function reports them through :func:`resolve_group_codes`.
    """
    if not isinstance(policy, dict):
        return ()
    collected: dict[str, None] = {}
    for key in POLICY_CHANNEL_KEYS:
        for code in _string_list(policy.get(key)):
            collected.setdefault(code, None)
    return tuple(collected)


def resolve_group_codes(policy: object) -> tuple[str, ...]:
    """Return the distinct notification group codes named by ``policy``."""
    if not isinstance(policy, dict):
        return ()
    collected: dict[str, None] = {}
    for key in POLICY_GROUP_KEYS:
        for code in _string_list(policy.get(key)):
            collected.setdefault(code, None)
    return tuple(collected)


def _string_list(raw: object) -> list[str]:
    if isinstance(raw, str):
        # A single code written as a string is a common configuration slip.
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return []
    codes: list[str] = []
    for item in raw:
        code = str(item).strip()
        if code:
            codes.append(code)
    return codes


class NotificationDispatcher:
    """Turns one alert into one delivery attempt per configured channel."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        registry: NotificationRegistry | None = None,
    ) -> None:
        self._session = session
        self._alerts = AlertRepository(session)
        self._channels = NotificationRepository(session)
        self._maintenance = MaintenanceRepository(session)
        self._registry = registry if registry is not None else build_default_registry()

    @property
    def registry(self) -> NotificationRegistry:
        return self._registry

    async def dispatch(
        self,
        alert: OpsAlert,
        rule: OpsAlertRule,
        now: datetime.datetime,
    ) -> list[OpsAlertNotification]:
        """Deliver ``alert`` to every channel its rule names.

        Never raises: a delivery problem is a ``FAILED`` row, because losing one
        notification must never lose the alert that was just created.
        """
        policy = getattr(rule, "notification_policy", None)
        direct = resolve_channel_codes(policy)
        groups = resolve_group_codes(policy)
        # No policy at all: return before any read, so an unconfigured rule
        # costs nothing and notifies nobody.
        if not direct and not groups:
            return []
        codes = await self.expand_codes(direct=direct, groups=groups)
        if not codes:
            _LOGGER.warning(
                "alert notification policy names no usable channel rule_code=%s",
                getattr(rule, "rule_code", None),
            )
            return []
        records: list[OpsAlertNotification] = []
        for code in codes:
            try:
                records.append(await self._dispatch_one(alert, rule, code, now))
            except Exception as exc:  # noqa: BLE001 - one channel must not stop the rest
                _LOGGER.warning(
                    "alert notification dispatch failed channel=%s error=%s",
                    code,
                    f"{type(exc).__name__}: {exc}",
                )
                records.append(
                    await self._record(
                        alert,
                        channel_code=code,
                        channel_id=None,
                        status=NOTIFICATION_STATUS_FAILED,
                        error_message=f"{type(exc).__name__}: {exc}",
                        receiver=None,
                        now=now,
                    )
                )
        return records

    async def expand_codes(
        self,
        *,
        direct: tuple[str, ...] = (),
        groups: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        """Expand group codes into the channel codes they carry, deduplicated."""
        collected: dict[str, None] = {code: None for code in direct}
        if groups:
            rows = await self._channels.list_groups_by_codes(groups)
            for row in rows:
                for code in _string_list(row.channel_codes):
                    collected.setdefault(code, None)
        return tuple(collected)

    async def _dispatch_one(
        self,
        alert: OpsAlert,
        rule: OpsAlertRule,
        channel_code: str,
        now: datetime.datetime,
    ) -> OpsAlertNotification:
        channel = await self._channels.get_channel_by_code(channel_code)
        if channel is None or not bool(channel.enabled):
            # The rule names a channel that no longer exists: say so instead of
            # silently dropping the notification.
            return await self._record(
                alert,
                channel_code=channel_code,
                channel_id=None,
                status=NOTIFICATION_STATUS_FAILED,
                error_message="notification channel is missing or disabled",
                receiver=None,
                now=now,
            )
        skip_reason = await self._skip_reason(alert, rule, now)
        if skip_reason is not None:
            return await self._record(
                alert,
                channel_code=channel_code,
                channel_id=int(channel.id),
                status=NOTIFICATION_STATUS_SKIPPED,
                error_message=skip_reason,
                receiver=None,
                now=now,
            )
        provider = self._provider(channel)
        if provider is None:
            return await self._record(
                alert,
                channel_code=channel_code,
                channel_id=int(channel.id),
                status=NOTIFICATION_STATUS_FAILED,
                error_message=f"no provider for channel type {channel.channel_type}",
                receiver=None,
                now=now,
            )
        result = await self._send(provider, alert, channel)
        return await self._record(
            alert,
            channel_code=channel_code,
            channel_id=int(channel.id),
            status=result.status,
            error_message=result.error_message,
            receiver=result.receiver or None,
            now=now,
        )

    def _provider(self, channel: OpsNotificationChannel) -> NotificationChannel | None:
        try:
            return self._registry.get(str(channel.channel_type))
        except UnsupportedChannelError:
            return None

    async def _send(
        self,
        provider: NotificationChannel,
        alert: OpsAlert,
        channel: OpsNotificationChannel,
    ) -> NotificationResult:
        try:
            return await provider.send(alert, channel)
        except Exception as exc:  # noqa: BLE001 - a provider bug is a FAILED row
            return NotificationResult(
                status=NOTIFICATION_STATUS_FAILED,
                error_message=f"{type(exc).__name__}: {exc}"[:_MAX_ERROR_MESSAGE_LENGTH],
            )

    async def _skip_reason(
        self,
        alert: OpsAlert,
        rule: OpsAlertRule,
        now: datetime.datetime,
    ) -> str | None:
        """Return why this alert must not be sent right now, or ``None``."""
        silenced_until = getattr(alert, "silenced_until", None)
        if silenced_until is not None and silenced_until > now:
            return f"alert silenced until {silenced_until.isoformat()}"
        window = await self._maintenance.find_suppressing(
            at=now,
            scope_type=_scope_type(rule, alert),
            scope_id=_scope_id(rule, alert),
        )
        if window is not None:
            return f"suppressed by maintenance window {window.window_code}"
        return None

    async def _record(
        self,
        alert: OpsAlert,
        *,
        channel_code: str,
        channel_id: int | None,
        status: str,
        error_message: str | None,
        receiver: str | None,
        now: datetime.datetime,
    ) -> OpsAlertNotification:
        return await self._alerts.add_notification(
            id=new_id(),
            alert_id=int(alert.id),
            channel_id=channel_id,
            channel_code=channel_code,
            receiver=receiver,
            status=status,
            retry_count=0,
            sent_at=now if status == NOTIFICATION_STATUS_SENT else None,
            error_message=(
                error_message[:_MAX_ERROR_MESSAGE_LENGTH] if error_message else None
            ),
            created_at=now,
            updated_at=now,
        )


def _scope_type(rule: OpsAlertRule, alert: OpsAlert) -> str | None:
    """The scope a maintenance window is matched against.

    The rule owns the scope: an alert inherits it, and a manual alert may carry
    no scope at all.
    """
    value = getattr(rule, "scope_type", None)
    if value is None:
        value = getattr(alert, "resource_type", None)
    return str(value) if value is not None else None


def _scope_id(rule: OpsAlertRule, alert: OpsAlert) -> int | None:
    value = getattr(rule, "scope_id", None)
    if value is None:
        value = getattr(alert, "resource_id", None)
    if value is None:
        value = getattr(alert, "host_id", None)
    if value is None:
        value = getattr(alert, "service_id", None)
    return None if value is None else int(value)  # type: ignore[arg-type]
