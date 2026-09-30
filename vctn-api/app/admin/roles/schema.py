"""app.admin.roles — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, StringId


class CreateRoleRequest(ApiModel):
    """Create a role."""

    role_code: str = Field(min_length=1, max_length=64)
    role_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    data_scope: str = "SELF"
    custom_department_ids: list[StringId] = Field(default_factory=list)


class UpdateRoleRequest(ApiModel):
    """Update a role."""

    role_name: str | None = Field(default=None, max_length=128)
    description: str | None = None
    status: str | None = None
    data_scope: str | None = None
    custom_department_ids: list[StringId] | None = None


class RoleResponse(ApiModel):
    """Role detail."""

    id: StringId
    role_code: str
    role_name: str
    description: str | None = None
    status: str
    data_scope: str
    custom_department_ids: list[StringId] = Field(default_factory=list)
    user_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AssignPermissionsRequest(ApiModel):
    """Replace the permission set of a role."""

    permission_ids: list[StringId] = Field(default_factory=list)


class PermissionBrief(ApiModel):
    """Permission summary."""

    id: StringId
    permission_code: str
    permission_name: str
    permission_type: str
    resource_type: str
    resource_code: str


class AssignParentsRequest(ApiModel):
    """Replace the parent roles a role inherits from."""

    parent_role_ids: list[StringId] = Field(default_factory=list)


class ParentRoleBrief(ApiModel):
    """Parent role summary."""

    id: StringId
    role_code: str
    role_name: str
    data_scope: str
