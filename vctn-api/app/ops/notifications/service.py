"""app.ops.notifications — business logic.

Channel configuration is sanitized before it is stored: only non sensitive keys
survive (``url``, ``method``, ``headers``, ``template``, ``timeout_seconds``),
so a token or a secret can never be persisted in ``ops_notification_channel``.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.alerts.model import OpsAlertNotification
from app.ops.alerts.schema import AlertNotificationResponse
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.notifications.model import OpsNotificationChannel
from app.ops.notifications.providers import CHANNEL_TYPES
from app.ops.notifications.repository import NotificationRepository
from app.ops.notifications.schema import (
    NotificationChannelCreateRequest,
    NotificationChannelResponse,
    NotificationChannelUpdateRequest,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

#: The only channel configuration keys that may be persisted.
ALLOWED_CONFIG_KEYS: frozenset[str] = frozenset(
    {"url", "method", "headers", "template", "timeout_seconds"}
)
_SENSITIVE_KEY_TOKENS: tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "key",
    "credential",
)


class NotificationService:
    """Notification records and channel configuration."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = NotificationRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_notifications(
        self,
        *,
        status: str | None = None,
        alert_id: int | None = None,
        page: PageParams,
    ) -> Page[AlertNotificationResponse]:
        rows, total = await self._repository.list_notifications(
            status=status,
            alert_id=alert_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_notification_response(row) for row in rows],
            total=total,
            params=page,
        )

    async def list_channels(
        self,
        *,
        keyword: str | None = None,
        channel_type: str | None = None,
        enabled: bool | None = None,
        page: PageParams,
    ) -> Page[NotificationChannelResponse]:
        rows, total = await self._repository.list_channels(
            keyword=keyword,
            channel_type=channel_type,
            enabled=enabled,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_channel_response(row) for row in rows],
            total=total,
            params=page,
        )

    async def create_channel(
        self, actor: Principal, payload: NotificationChannelCreateRequest
    ) -> NotificationChannelResponse:
        channel_code = payload.channel_code.strip()
        if not channel_code:
            raise ValidationError("channel_code is required")
        if not payload.channel_name.strip():
            raise ValidationError("channel_name is required")
        self._validate_channel_type(payload.channel_type)
        if await self._repository.get_channel_by_code(channel_code):
            raise ConflictError("channel_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create_channel(
            id=new_id(),
            channel_code=channel_code,
            channel_name=payload.channel_name,
            channel_type=payload.channel_type,
            config=self._sanitize_config(payload.config),
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_NOTIFICATION_CHANNEL_CREATE",
            actor=actor,
            resource_type="ops_notification_channel",
            resource_id=int(row.id),
            after_data={"channel_code": channel_code, "channel_type": payload.channel_type},
        )
        await write_operation_log(
            self._session,
            operation="OPS_NOTIFICATION_CHANNEL_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_notification_channel",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_channel_response(row)

    async def update_channel(
        self, actor: Principal, channel_id: int, payload: NotificationChannelUpdateRequest
    ) -> NotificationChannelResponse:
        row = await self._repository.get_channel(channel_id)
        if row is None:
            raise NotFoundError("notification channel not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "channel_type" in changes:
            self._validate_channel_type(str(changes["channel_type"]))
        if "config" in changes:
            changes["config"] = self._sanitize_config(changes["config"])
        before = {"channel_type": row.channel_type, "enabled": row.enabled}
        await self._repository.update_channel(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_NOTIFICATION_CHANNEL_UPDATE",
            actor=actor,
            resource_type="ops_notification_channel",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_NOTIFICATION_CHANNEL_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_notification_channel",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_channel_response(row)

    @staticmethod
    def _validate_channel_type(channel_type: str) -> None:
        if channel_type not in CHANNEL_TYPES:
            raise ValidationError(
                f"channel_type must be one of {sorted(CHANNEL_TYPES)}; "
                "V1 registers the Webhook provider only"
            )

    @classmethod
    def _sanitize_config(cls, config: dict) -> dict:
        """Keep non sensitive keys only and refuse anything else."""
        if not isinstance(config, dict):
            raise ValidationError("config must be an object")
        sanitized: dict[str, object] = {}
        rejected: list[str] = []
        for key, value in config.items():
            name = str(key)
            if name not in ALLOWED_CONFIG_KEYS or cls._is_sensitive_key(name):
                rejected.append(name)
                continue
            sanitized[name] = cls._sanitize_value(name, value)
        if rejected:
            raise ValidationError(
                f"config keys {sorted(rejected)} are not allowed; "
                f"allowed keys: {sorted(ALLOWED_CONFIG_KEYS)}"
            )
        if not sanitized:
            raise ValidationError("config must not be empty")
        return sanitized

    @classmethod
    def _sanitize_value(cls, key: str, value: object) -> object:
        if key != "headers":
            return value
        if not isinstance(value, dict):
            raise ValidationError("config.headers must be an object")
        headers: dict[str, object] = {}
        rejected: list[str] = []
        for header_name, header_value in value.items():
            name = str(header_name)
            if cls._is_sensitive_key(name):
                rejected.append(name)
                continue
            headers[name] = header_value
        if rejected:
            raise ValidationError(f"header names {sorted(rejected)} may carry credentials")
        return headers

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        lowered = key.lower()
        return any(token in lowered for token in _SENSITIVE_KEY_TOKENS)

    @staticmethod
    def _to_channel_response(row: OpsNotificationChannel) -> NotificationChannelResponse:
        return NotificationChannelResponse(
            id=str(int(row.id)),
            channel_code=str(row.channel_code),
            channel_name=str(row.channel_name),
            channel_type=str(row.channel_type),
            config=dict(row.config or {}),
            enabled=bool(row.enabled),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_notification_response(row: OpsAlertNotification) -> AlertNotificationResponse:
        return AlertNotificationResponse(
            id=str(int(row.id)),
            alert_id=str(int(row.alert_id)),
            channel_id=str(int(row.channel_id)) if row.channel_id is not None else None,
            channel_code=str(row.channel_code),
            receiver=row.receiver,
            status=str(row.status),
            retry_count=int(row.retry_count),
            sent_at=row.sent_at,
            error_message=row.error_message,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
