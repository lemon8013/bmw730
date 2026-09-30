"""app.admin.config — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.config.model import SysFeatureFlag
from app.admin.config.repository import ConfigRepository
from app.admin.config.schema import (
    ConfigResponse,
    CreateFeatureFlagRequest,
    FeatureFlagResponse,
    UpdateConfigRequest,
    UpdateFeatureFlagRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams

ACTIVE_STATUS: str = "ACTIVE"


class ConfigService:
    """Configuration entries and feature flags."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ConfigRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_configs(self, *, page: PageParams) -> Page[ConfigResponse]:
        rows = await self._repository.list_configs()
        items = [ConfigResponse.model_validate(row) for row in rows]
        total = len(items)
        return Page.build(
            items=items[page.offset : page.offset + page.limit], total=total, params=page
        )

    async def update_config(
        self, actor: Principal, key: str, payload: UpdateConfigRequest
    ) -> ConfigResponse:
        """Update one editable configuration entry, bumping its version."""
        row = await self._repository.get_config_by_key(key)
        if row is None:
            raise NotFoundError("configuration entry not found")
        if not bool(row.editable):
            await self._audit.record_failure(
                self._session,
                action="CONFIG_EDIT",
                error_code="CONFIG_NOT_EDITABLE",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_config",
                resource_id=str(row.config_key),
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("this configuration entry is not editable")
        validate_config_value(str(row.value_type), payload.config_value)

        before = {"config_value": row.config_value, "version": row.version}
        row.config_value = payload.config_value
        row.version = int(row.version or 0) + 1
        row.effective_at = datetime.datetime.now(datetime.UTC)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="CONFIG_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_config",
            resource_id=str(row.config_key),
            before_data=before,
            after_data={
                "config_value": row.config_value,
                "version": row.version,
                "reason": payload.reason,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return ConfigResponse.model_validate(row)

    async def list_flags(self, *, page: PageParams) -> Page[FeatureFlagResponse]:
        rows = await self._repository.list_flags()
        items = [FeatureFlagResponse.model_validate(row) for row in rows]
        total = len(items)
        return Page.build(
            items=items[page.offset : page.offset + page.limit], total=total, params=page
        )

    async def create_flag(
        self, actor: Principal, payload: CreateFeatureFlagRequest
    ) -> FeatureFlagResponse:
        if await self._repository.exists_flag_key(payload.flag_key):
            raise ConflictError("feature flag key is already taken")
        row = SysFeatureFlag(
            id=new_id(),
            flag_key=payload.flag_key,
            flag_name=payload.flag_name,
            enabled=payload.enabled,
            strategy=payload.strategy,
            percentage=payload.percentage,
            conditions=payload.conditions,
            description=payload.description,
            version=1,
        )
        self._repository.add_flag(row)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="FEATURE_FLAG_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_feature_flag",
            resource_id=int(row.id),
            after_data={"flag_key": row.flag_key, "enabled": row.enabled},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return FeatureFlagResponse.model_validate(row)

    async def update_flag(
        self, actor: Principal, flag_id: int, payload: UpdateFeatureFlagRequest
    ) -> FeatureFlagResponse:
        row = await self._repository.get_flag(flag_id)
        if row is None:
            raise NotFoundError("feature flag not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        before = {
            "flag_name": row.flag_name,
            "strategy": row.strategy,
            "percentage": row.percentage,
        }
        for field_name, value in changes.items():
            setattr(row, field_name, value)
        row.version = int(row.version or 0) + 1
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="FEATURE_FLAG_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_feature_flag",
            resource_id=flag_id,
            before_data=before,
            after_data={
                "flag_name": row.flag_name,
                "strategy": row.strategy,
                "percentage": row.percentage,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return FeatureFlagResponse.model_validate(row)

    async def set_flag_enabled(
        self, actor: Principal, flag_id: int, *, enabled: bool
    ) -> FeatureFlagResponse:
        row = await self._repository.get_flag(flag_id)
        if row is None:
            raise NotFoundError("feature flag not found")
        before = {"enabled": row.enabled}
        row.enabled = enabled
        row.version = int(row.version or 0) + 1
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="FEATURE_FLAG_ENABLE" if enabled else "FEATURE_FLAG_DISABLE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_feature_flag",
            resource_id=flag_id,
            before_data=before,
            after_data={"enabled": row.enabled},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return FeatureFlagResponse.model_validate(row)


def validate_config_value(value_type: str, value: str) -> None:
    """Reject a value that does not match the declared configuration type."""
    lowered = value_type.lower()
    if lowered in ("int", "integer", "number"):
        try:
            int(value)
        except ValueError as exc:
            raise ValidationError("the value must be an integer") from exc
    elif lowered in ("bool", "boolean"):
        if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
            raise ValidationError("the value must be a boolean")
    elif lowered == "json":
        import json

        try:
            json.loads(value)
        except ValueError as exc:
            raise ValidationError("the value must be valid JSON") from exc
