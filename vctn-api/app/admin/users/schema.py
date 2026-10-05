"""app.admin.users — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import (
    ApiModel,
    OptionalIpAddress,
    OptionalStringId,
    StringId,
)


class UserListQuery(ApiModel):
    """Filters accepted by ``GET /users``."""

    keyword: str | None = None
    department_id: OptionalStringId = None
    status: str | None = None


class CreateUserRequest(ApiModel):
    """Create an administrator."""

    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    email: str | None = None
    phone: str | None = None
    department_id: OptionalStringId = None
    role_ids: list[StringId] = Field(default_factory=list)
    temporary_password: str | None = None


class UpdateUserRequest(ApiModel):
    """Update an administrator."""

    display_name: str | None = Field(default=None, max_length=128)
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    department_id: OptionalStringId = None


class MoveDepartmentRequest(ApiModel):
    """Move an administrator to another department."""

    department_id: OptionalStringId = None


class AssignRolesRequest(ApiModel):
    """Replace the role set of an administrator."""

    role_ids: list[StringId] = Field(default_factory=list)


class ForceLogoutRequest(ApiModel):
    """Force logout payload."""

    reason: str | None = Field(default=None, max_length=255)


class BatchForceLogoutRequest(ApiModel):
    """Batch force logout payload."""

    user_ids: list[StringId] = Field(default_factory=list)
    reason: str | None = Field(default=None, max_length=255)


class UserResponse(ApiModel):
    """Administrator detail."""

    id: StringId
    username: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    department_id: OptionalStringId = None
    department_name: str | None = None
    status: str
    is_super_admin: bool
    must_change_password: bool
    password_changed_at: datetime.datetime | None = None
    password_expires_at: datetime.datetime | None = None
    failed_login_count: int
    locked_until: datetime.datetime | None = None
    last_login_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    roles: list[RoleBrief] = Field(default_factory=list)
    # Only ever populated by the create response: the generated password is
    # returned once and never stored in a log or an audit record.
    temporary_password: str | None = None


class RoleBrief(ApiModel):
    """Role summary carried by a user payload."""

    id: StringId
    role_code: str
    role_name: str
    data_scope: str


class OnlineUserResponse(ApiModel):
    """One online administrator."""

    user_id: StringId
    username: str
    display_name: str
    department_id: OptionalStringId = None
    session_id: StringId
    ip: OptionalIpAddress = None
    device_type: str | None = None
    login_at: datetime.datetime
    last_active_at: datetime.datetime | None = None


class ForceLogoutResponse(ApiModel):
    """Result of a forced logout."""

    user_id: StringId
    revoked_sessions: int


UserResponse.model_rebuild()
