"""app.admin.config — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, StringId


class ConfigResponse(ApiModel):
    """One configuration entry."""

    id: StringId
    config_key: str
    config_name: str
    config_group: str | None = None
    value_type: str
    config_value: str | None = None
    default_value: str | None = None
    editable: bool
    requires_restart: bool
    status: str
    description: str | None = None
    version: int
    effective_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class UpdateConfigRequest(ApiModel):
    """Update one configuration entry by key."""

    config_value: str = Field(max_length=4000)
    reason: str | None = Field(default=None, max_length=500)


class CreateFeatureFlagRequest(ApiModel):
    """Create a feature flag."""

    flag_key: str = Field(min_length=1, max_length=128)
    flag_name: str = Field(min_length=1, max_length=128)
    enabled: bool = False
    strategy: str = "ALL"
    percentage: int = Field(default=100, ge=0, le=100)
    conditions: dict | None = None
    description: str | None = None


class UpdateFeatureFlagRequest(ApiModel):
    """Update a feature flag."""

    flag_name: str | None = Field(default=None, max_length=128)
    strategy: str | None = None
    percentage: int | None = Field(default=None, ge=0, le=100)
    conditions: dict | None = None
    description: str | None = None


class FeatureFlagResponse(ApiModel):
    """Feature flag detail."""

    id: StringId
    flag_key: str
    flag_name: str
    enabled: bool
    strategy: str
    percentage: int | None = None
    conditions: dict | None = None
    description: str | None = None
    version: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
