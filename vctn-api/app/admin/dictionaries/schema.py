"""app.admin.dictionaries — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, StringId


class CreateDictTypeRequest(ApiModel):
    """Create a dictionary type."""

    dict_code: str = Field(min_length=1, max_length=128)
    dict_name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class UpdateDictTypeRequest(ApiModel):
    """Update a dictionary type."""

    dict_name: str | None = Field(default=None, max_length=128)
    description: str | None = None
    status: str | None = None


class DictTypeResponse(ApiModel):
    """Dictionary type detail."""

    id: StringId
    dict_code: str
    dict_name: str
    description: str | None = None
    status: str
    item_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime


class CreateDictItemRequest(ApiModel):
    """Create a dictionary item."""

    item_label: str = Field(min_length=1, max_length=128)
    item_value: str = Field(min_length=1, max_length=255)
    item_code: str | None = Field(default=None, max_length=128)
    sort_order: int = 0
    is_default: bool = False
    description: str | None = None


class UpdateDictItemRequest(ApiModel):
    """Update a dictionary item."""

    item_label: str | None = Field(default=None, max_length=128)
    item_value: str | None = Field(default=None, max_length=255)
    item_code: str | None = Field(default=None, max_length=128)
    sort_order: int | None = None
    is_default: bool | None = None
    status: str | None = None
    description: str | None = None


class DictItemResponse(ApiModel):
    """Dictionary item detail."""

    id: StringId
    dict_type_id: StringId
    item_label: str
    item_value: str
    item_code: str | None = None
    sort_order: int
    status: str
    is_default: bool
    description: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
