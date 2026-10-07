"""app.ops.notifications — channel providers (OPS-DECISION-009).

A channel is dispatched through the registry, never through an
``if channel_type == ...`` branch: adding a channel means adding a provider and
registering it in :func:`build_default_registry`.

A provider never raises: a delivery failure is a ``FAILED`` result carrying the
error message, so one broken channel cannot break alert evaluation.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final, Protocol
from urllib.parse import urlparse

from app.ops.notifications.model import OpsNotificationChannel

#: Supported channel types. V1 ships Webhook only.
CHANNEL_TYPE_WEBHOOK: Final[str] = "WEBHOOK"
CHANNEL_TYPES: Final[frozenset[str]] = frozenset({CHANNEL_TYPE_WEBHOOK})

NOTIFICATION_STATUS_PENDING: Final[str] = "PENDING"
NOTIFICATION_STATUS_SENT: Final[str] = "SENT"
NOTIFICATION_STATUS_FAILED: Final[str] = "FAILED"
NOTIFICATION_STATUS_SKIPPED: Final[str] = "SKIPPED"

DEFAULT_TIMEOUT_SECONDS: Final[int] = 5
MAX_TIMEOUT_SECONDS: Final[int] = 30
MAX_ERROR_MESSAGE_LENGTH: Final[int] = 1000

_ALLOWED_URL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


class UnsupportedChannelError(Exception):
    """No provider is registered for the requested channel type."""


class AlertLike(Protocol):
    """The alert facts a provider is allowed to serialize."""

    id: int
    fingerprint: str
    alert_type: str
    severity: str
    status: str
    metric_key: str | None
    metric_value: float | None
    threshold: float | None
    description: str | None
    triggered_at: datetime.datetime


@dataclass(frozen=True, slots=True)
class NotificationResult:
    """The outcome of one delivery attempt."""

    status: str
    receiver: str = ""
    error_message: str | None = None

    @property
    def sent(self) -> bool:
        return self.status == NOTIFICATION_STATUS_SENT


class NotificationChannel(ABC):
    """A delivery channel. Implementations must never raise."""

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """The channel type this provider serves."""

    @abstractmethod
    async def send(self, alert: AlertLike, channel: OpsNotificationChannel) -> NotificationResult:
        """Deliver one alert through one channel configuration."""


class NotificationRegistry:
    """Maps a channel type onto its provider."""

    def __init__(self, providers: dict[str, NotificationChannel]) -> None:
        self._providers = dict(providers)

    def register(self, provider: NotificationChannel) -> None:
        self._providers[provider.channel_type] = provider

    def get(self, channel_type: str) -> NotificationChannel:
        provider = self._providers.get(channel_type)
        if provider is None:
            raise UnsupportedChannelError(f"no provider registered for {channel_type}")
        return provider

    @property
    def channel_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


class WebhookProvider(NotificationChannel):
    """Posts a JSON alert payload to a webhook URL with stdlib urllib."""

    @property
    def channel_type(self) -> str:
        return CHANNEL_TYPE_WEBHOOK

    async def send(self, alert: AlertLike, channel: OpsNotificationChannel) -> NotificationResult:
        config = channel.config if isinstance(channel.config, dict) else {}
        url = str(config.get("url") or "").strip()
        if not url:
            return NotificationResult(
                status=NOTIFICATION_STATUS_FAILED,
                error_message="webhook url is not configured",
            )
        if urlparse(url).scheme not in _ALLOWED_URL_SCHEMES:
            return NotificationResult(
                status=NOTIFICATION_STATUS_FAILED,
                error_message="webhook url must use http or https",
            )
        timeout = self._resolve_timeout(config.get("timeout_seconds"))
        if timeout is None:
            return NotificationResult(
                status=NOTIFICATION_STATUS_FAILED,
                error_message="timeout_seconds must be an integer",
            )
        payload = json.dumps(self._payload(alert, channel)).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=payload,
            headers={"Content-Type": "application/json", **self._headers(config)},
            method="POST",
        )
        try:
            await asyncio.to_thread(
                lambda: urllib.request.urlopen(  # noqa: S310 - scheme validated above
                    request, timeout=timeout
                )
            )
        except urllib.error.URLError as exc:
            return self._failure(f"URLError: {exc.reason}")
        except TimeoutError:
            return self._failure(f"webhook timed out after {timeout}s")
        except Exception as exc:  # noqa: BLE001 - 渠道故障必须降级为 FAILED
            return self._failure(f"{type(exc).__name__}: {exc}")
        return NotificationResult(status=NOTIFICATION_STATUS_SENT, receiver=url)

    @staticmethod
    def _resolve_timeout(raw: object) -> int | None:
        if raw is None:
            return DEFAULT_TIMEOUT_SECONDS
        if isinstance(raw, bool) or not isinstance(raw, int):
            return None
        if raw <= 0:
            return None
        return min(int(raw), MAX_TIMEOUT_SECONDS)

    @staticmethod
    def _headers(config: dict[str, object]) -> dict[str, str]:
        headers = config.get("headers")
        if not isinstance(headers, dict):
            return {}
        # 只透传非敏感头：凭据永远不会离开配置存储，也不会被写进通知记录。
        return {
            str(key): str(value)
            for key, value in headers.items()
            if str(key).strip() and not _is_sensitive_key(str(key))
        }

    @staticmethod
    def _payload(alert: AlertLike, channel: OpsNotificationChannel) -> dict[str, object]:
        return {
            "event": "ALERT",
            "channel_code": str(channel.channel_code),
            "channel_type": str(channel.channel_type),
            "alert": {
                "id": str(int(alert.id)),
                "fingerprint": str(alert.fingerprint),
                "alert_type": str(alert.alert_type),
                "severity": str(alert.severity),
                "status": str(alert.status),
                "metric_key": alert.metric_key,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "description": alert.description,
                "triggered_at": alert.triggered_at.isoformat(),
            },
        }

    @staticmethod
    def _failure(message: str) -> NotificationResult:
        return NotificationResult(
            status=NOTIFICATION_STATUS_FAILED,
            error_message=message[:MAX_ERROR_MESSAGE_LENGTH],
        )


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("token", "secret", "password", "auth"))


def build_default_registry() -> NotificationRegistry:
    """Return the registry used by the application: Webhook only in V1."""
    registry = NotificationRegistry({})
    registry.register(WebhookProvider())
    return registry
