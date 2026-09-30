"""app.admin.permissions — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class FieldPermissionInput(ApiModel):
    """One field policy attached to a permission resource."""

    field_code: str = Field(min_length=1, max_length=128)
    field_mode: str = Field(pattern="^(VISIBLE|HIDDEN|READ_ONLY|EDITABLE)$")


class CreateResourceRequest(ApiModel):
    """Create a permission resource."""

    permission_code: str = Field(min_length=1, max_length=128)
    permission_name: str = Field(min_length=1, max_length=128)
    permission_type: str = Field(pattern="^(API|MENU|PAGE|BUTTON|FIELD)$")
    resource_type: str = Field(min_length=1, max_length=64)
    resource_code: str = Field(min_length=1, max_length=255)
    parent_id: OptionalStringId = None
    sort_order: int = 0
    description: str | None = None
    field_permissions: list[FieldPermissionInput] = Field(default_factory=list)


class UpdateResourceRequest(ApiModel):
    """Update a permission resource."""

    permission_name: str | None = Field(default=None, max_length=128)
    resource_type: str | None = Field(default=None, max_length=64)
    resource_code: str | None = Field(default=None, max_length=255)
    parent_id: OptionalStringId = None
    sort_order: int | None = None
    status: str | None = None
    description: str | None = None
    field_permissions: list[FieldPermissionInput] | None = None


class FieldPermissionOutput(ApiModel):
    """One field policy as stored."""

    id: StringId
    field_code: str
    field_mode: str


class PermissionResourceResponse(ApiModel):
    """Permission resource detail."""

    id: StringId
    permission_code: str
    permission_name: str
    permission_type: str
    resource_type: str
    resource_code: str
    parent_id: OptionalStringId = None
    status: str
    sort_order: int
    description: str | None = None
    field_permissions: list[FieldPermissionOutput] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime


class PermissionTreeNode(ApiModel):
    """One node of the permission tree."""

    id: StringId
    permission_code: str
    permission_name: str
    permission_type: str
    resource_type: str
    resource_code: str
    status: str
    sort_order: int
    children: list[PermissionTreeNode] = Field(default_factory=list)


PermissionTreeNode.model_rebuild()
