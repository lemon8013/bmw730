"""app.admin.auth — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import (
    ApiModel,
    OptionalIpAddress,
    OptionalStringId,
    StringId,
)


class LoginRequest(ApiModel):
    """Administrator login payload."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(ApiModel):
    """Issued credential pair."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int


class LoginResponse(ApiModel):
    """Login result."""

    token: TokenResponse
    must_change_password: bool
    password_expired: bool


class RefreshRequest(ApiModel):
    """Refresh payload: the refresh token travels in the request body."""

    refresh_token: str = Field(min_length=8, max_length=512)


class LogoutRequest(ApiModel):
    """Logout payload."""

    refresh_token: str | None = None


class ChangePasswordRequest(ApiModel):
    """Self service password change."""

    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class ResetPasswordRequest(ApiModel):
    """Administrative password reset for another account."""

    user_id: StringId
    reason: str | None = Field(default=None, max_length=500)


class ResetPasswordResponse(ApiModel):
    """The generated temporary password is returned once and never logged."""

    user_id: StringId
    temporary_password: str
    must_change_password: bool


class AdminUserBrief(ApiModel):
    """Administrator summary."""

    id: StringId
    username: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    department_id: OptionalStringId = None
    status: str
    is_super_admin: bool
    must_change_password: bool
    last_login_at: datetime.datetime | None = None
    created_at: datetime.datetime


class MenuNode(ApiModel):
    """One node of the dynamic menu tree."""

    id: StringId
    permission_code: str
    permission_name: str
    resource_type: str
    resource_code: str
    parent_id: OptionalStringId = None
    sort_order: int


class CurrentUserResponse(ApiModel):
    """/auth/me payload."""

    user: AdminUserBrief
    permissions: list[str]
    is_super_admin: bool
    must_change_password: bool
    password_expired: bool


class PermissionsResponse(ApiModel):
    """/auth/permissions payload."""

    permissions: list[str]
    menus: list[MenuNode]
    is_super_admin: bool


class SessionBrief(ApiModel):
    """One session row."""

    id: StringId
    user_id: StringId
    session_status: str
    ip: OptionalIpAddress = None
    device_type: str | None = None
    login_at: datetime.datetime
    last_active_at: datetime.datetime | None = None
    expires_at: datetime.datetime
    revoked_at: datetime.datetime | None = None
    revoke_reason: str | None = None


class MfaFactorBrief(ApiModel):
    """MFA factor without its secret."""

    id: StringId
    user_id: StringId
    factor_type: str
    status: str
    verified_at: datetime.datetime | None = None
