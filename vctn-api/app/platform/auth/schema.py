"""app.platform.auth — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import (
    ApiModel,
    OptionalIpAddress,
    StringId,
)


class RegisterRequest(ApiModel):
    """Business user registration."""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    nickname: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(ApiModel):
    """Business user login by username, email or phone."""

    identity: str = Field(min_length=1, max_length=320)
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
    user_id: StringId
    nickname: str | None = None
    must_change_password: bool = False


class RefreshRequest(ApiModel):
    """Refresh payload."""

    refresh_token: str = Field(min_length=8, max_length=512)


class LogoutRequest(ApiModel):
    """Logout payload."""

    refresh_token: str | None = None


class ChangePasswordRequest(ApiModel):
    """Self service password change."""

    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class SendVerificationRequest(ApiModel):
    """Request a verification code."""

    verification_type: str = Field(pattern="^(EMAIL|PHONE)$")
    target: str = Field(min_length=3, max_length=320)


class SendVerificationResponse(ApiModel):
    """Verification challenge.

    No notification provider is frozen, so ``delivery`` reports what actually
    happened instead of claiming an email or SMS was sent.
    """

    verification_id: StringId
    verification_type: str
    target_masked: str
    expires_at: datetime.datetime
    delivery: str
    debug_code: str | None = None


class VerifyRequest(ApiModel):
    """Submit a verification code."""

    verification_id: StringId
    code: str = Field(min_length=4, max_length=16)


class VerifyResponse(ApiModel):
    """Verification result."""

    verification_id: StringId
    verified: bool
    identity_type: str


class PlatformUserBrief(ApiModel):
    """Business user summary."""

    id: StringId
    username: str | None = None
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    status: str
    registered_at: datetime.datetime | None = None
    last_login_at: datetime.datetime | None = None


class PlatformSessionBrief(ApiModel):
    """One business user session."""

    id: StringId
    session_status: str
    device_type: str | None = None
    login_at: datetime.datetime
    last_active_at: datetime.datetime | None = None
    expires_at: datetime.datetime
    revoked_at: datetime.datetime | None = None
    revoke_reason: str | None = None
    ip: OptionalIpAddress = None
