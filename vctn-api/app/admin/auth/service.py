"""app.admin.auth — business logic.

The service owns the transaction: login, refresh, logout and password changes
each write their rows, their audit record and their security log in one unit of
work that the caller commits.

Passwords are never written to a log, an audit record or an exception message -
only the event ("LOGIN_FAILURE", "PASSWORD_CHANGED") is recorded.
"""

from __future__ import annotations

import datetime
import secrets
import string
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysMfaFactor
from app.admin.auth.repository import AdminAuthRepository
from app.admin.auth.schema import (
    AdminUserBrief,
    CurrentUserResponse,
    MenuNode,
    PermissionsResponse,
    ResetPasswordResponse,
    SessionBrief,
    TokenResponse,
)
from app.admin.users.model import SysUser
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
)
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.authorization.service import AuthorizationService
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_FAILURE, RESULT_SUCCESS, write_security_log
from app.shared.rate_limit.service import RateLimitService
from app.shared.security.mfa import get_registry
from app.shared.security.password import (
    hash_password,
    is_password_expired,
    lock_until_after_failures,
    password_expiry_at,
    validate_password_policy,
    verify_password,
)
from app.shared.security.tokens import (
    TokenPair,
    decode_access_token,
    hash_refresh_token,
    issue_token_pair,
)

ACTIVE_STATUS: str = "ACTIVE"
DISABLED_STATUS: str = "DISABLED"
MFA_ACTIVE_STATUS: str = "ACTIVE"
MFA_VERIFIED_STATUS: str = "VERIFIED"


class AdminAuthService:
    """Administrator authentication and password business logic."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        redis: aioredis.Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._repository = AdminAuthRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._authorization = AuthorizationService(self._settings)
        self._rate_limit = RateLimitService(redis, self._settings) if redis is not None else None

    # ------------------------------------------------------------------
    # Login / logout
    # ------------------------------------------------------------------
    async def login(
        self,
        *,
        username: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
        device_type: str | None = None,
    ) -> tuple[SysUser, TokenPair, bool]:
        """Authenticate an administrator.

        Returns the user, the issued token pair and whether the password is
        expired (which forces a password change).

        Raises:
            AuthenticationError: on unknown account, wrong password, disabled or
                locked account.
        """
        if self._rate_limit is not None:
            await self._rate_limit.enforce(
                bucket="login",
                subject=f"admin:{username.lower()}",
                limit=self._settings.RATE_LIMIT_LOGIN_PER_WINDOW,
            )

        user = await self._repository.find_user_by_username(username)
        now = datetime.datetime.now(datetime.UTC)

        if user is None:
            await write_security_log(
                self._session,
                event_type="LOGIN_FAILURE",
                result=RESULT_FAILURE,
                error_code="ACCOUNT_NOT_FOUND",
                ip=ip,
                user_agent=user_agent,
                metadata={"username": username},
            )
            await self._session.commit()
            raise AuthenticationError("invalid username or password")

        if user.status == DISABLED_STATUS:
            await write_security_log(
                self._session,
                event_type="LOGIN_FAILURE",
                result=RESULT_FAILURE,
                error_code="ACCOUNT_DISABLED",
                user_id=int(user.id),
                ip=ip,
                user_agent=user_agent,
            )
            await self._session.commit()
            raise AuthenticationError("account is disabled")

        if user.locked_until is not None and user.locked_until > now:
            await write_security_log(
                self._session,
                event_type="LOGIN_FAILURE",
                result=RESULT_FAILURE,
                error_code="ACCOUNT_LOCKED",
                user_id=int(user.id),
                ip=ip,
                user_agent=user_agent,
                metadata={"locked_until": user.locked_until.isoformat()},
            )
            await self._session.commit()
            raise AuthenticationError("account is locked")

        if not verify_password(password, str(user.password_hash)):
            await self._register_failed_attempt(user, now=now, ip=ip, user_agent=user_agent)
            raise AuthenticationError("invalid username or password")

        if await self._mfa_is_required(user):
            await write_security_log(
                self._session,
                event_type="MFA_REQUIRED",
                result=RESULT_FAILURE,
                error_code="MFA_REQUIRED",
                user_id=int(user.id),
                ip=ip,
                user_agent=user_agent,
            )
            await self._session.commit()
            raise AuthenticationError("multi factor verification is required")

        password_expired = is_password_expired(user.password_changed_at, now=now)
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        if ip is not None:
            user.last_login_ip = ip
        if password_expired:
            user.must_change_password = True
        await self._session.flush()

        await self._enforce_session_limit(user, now=now)
        session_row = await self._repository.create_session(
            user_id=int(user.id),
            refresh_token_hash="",
            ip=ip,
            user_agent=user_agent,
            device_type=device_type,
            login_at=now,
            expires_at=now
            + datetime.timedelta(seconds=self._settings.AUTH_REFRESH_TOKEN_TTL_SECONDS),
        )
        pair, refresh_digest, _, _ = issue_token_pair(
            subject_id=int(user.id),
            session_id=int(session_row.id),
            subject_type="admin",
            now=now,
            settings=self._settings,
        )
        session_row.refresh_token_hash = refresh_digest
        await self._session.flush()

        await write_security_log(
            self._session,
            event_type="LOGIN_SUCCESS",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        await self._audit.record(
            self._session,
            action="AUTH_LOGIN",
            operator_id=int(user.id),
            operator_username=str(user.username),
            resource_type="sys_user",
            resource_id=int(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
        return user, pair, password_expired

    async def _register_failed_attempt(
        self,
        user: SysUser,
        *,
        now: datetime.datetime,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        attempts = int(user.failed_login_count or 0) + 1
        user.failed_login_count = attempts
        if attempts >= self._settings.PASSWORD_MAX_FAILED_ATTEMPTS:
            user.locked_until = lock_until_after_failures(now, self._settings)
            await write_security_log(
                self._session,
                event_type="ACCOUNT_LOCKED",
                result=RESULT_FAILURE,
                error_code="ACCOUNT_LOCKED",
                user_id=int(user.id),
                ip=ip,
                user_agent=user_agent,
                metadata={"failed_attempts": attempts},
            )
        await self._session.flush()
        await write_security_log(
            self._session,
            event_type="LOGIN_FAILURE",
            result=RESULT_FAILURE,
            error_code="INVALID_PASSWORD",
            user_id=int(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"failed_attempts": attempts},
        )
        # The failure counter and its log must survive: the request is rejected
        # right after this point, so the unit of work is committed explicitly.
        await self._session.commit()

    async def _enforce_session_limit(self, user: SysUser, *, now: datetime.datetime) -> None:
        """Revoke the oldest sessions once the concurrent limit is reached."""
        limit = self._settings.AUTH_MAX_ACTIVE_SESSIONS_PER_USER
        stale = await self._repository.oldest_active_session_ids(int(user.id), max(0, limit - 1))
        if stale:
            await self._repository.revoke_sessions(stale, reason="SESSION_LIMIT", revoked_at=now)

    async def _mfa_is_required(self, user: SysUser) -> bool:
        """Return whether a usable MFA factor must be satisfied.

        A factor only blocks the login when a provider for its type is actually
        registered - an unfrozen provider must never lock an account out.
        """
        registry = get_registry()
        if registry.is_empty():
            return False
        rows = (
            (
                await self._session.execute(
                    select(SysMfaFactor).where(
                        SysMfaFactor.user_id == int(user.id),
                        SysMfaFactor.status == MFA_ACTIVE_STATUS,
                    )
                )
            )
            .scalars()
            .all()
        )
        return any(registry.get(str(row.factor_type)) is not None for row in rows)

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        """Rotate a refresh token and issue a new pair.

        Raises:
            AuthenticationError: when the refresh token is unknown, revoked or
                expired.
        """
        digest = hash_refresh_token(refresh_token)
        session_row = await self._repository.find_session_by_refresh_hash(digest)
        now = datetime.datetime.now(datetime.UTC)
        if (
            session_row is None
            or session_row.revoked_at is not None
            or session_row.session_status != "ACTIVE"
            or session_row.expires_at <= now
        ):
            await write_security_log(
                self._session,
                event_type="TOKEN_REFRESH",
                result=RESULT_FAILURE,
                error_code="INVALID_REFRESH_TOKEN",
                user_id=None if session_row is None else int(session_row.user_id),
            )
            await self._session.commit()
            raise AuthenticationError("invalid or expired refresh token")

        user = await self._repository.find_user_by_id(int(session_row.user_id))
        if user is None or user.status != ACTIVE_STATUS:
            raise AuthenticationError("account is not active")

        pair, new_digest, _, _ = issue_token_pair(
            subject_id=int(user.id),
            session_id=int(session_row.id),
            subject_type="admin",
            now=now,
            settings=self._settings,
        )
        session_row.refresh_token_hash = new_digest
        session_row.last_active_at = now
        session_row.expires_at = now + datetime.timedelta(
            seconds=self._settings.AUTH_REFRESH_TOKEN_TTL_SECONDS
        )
        await self._session.flush()
        await write_security_log(
            self._session,
            event_type="TOKEN_REFRESH",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
        )
        await self._session.commit()
        return pair

    async def logout(self, principal: Principal, *, reason: str = "LOGOUT") -> None:
        """Revoke the caller's current session."""
        now = datetime.datetime.now(datetime.UTC)
        revoked = await self._repository.revoke_sessions(
            [principal.session_id], reason=reason, revoked_at=now
        )
        await write_security_log(
            self._session,
            event_type="LOGOUT",
            result=RESULT_SUCCESS if revoked else RESULT_FAILURE,
            error_code=None if revoked else "SESSION_NOT_FOUND",
            user_id=principal.subject_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()

    # ------------------------------------------------------------------
    # Current user
    # ------------------------------------------------------------------
    async def current_user(self, principal: Principal) -> CurrentUserResponse:
        """Return the caller, its permissions and its password state."""
        user = await self._repository.find_user_by_id(principal.subject_id)
        if user is None:
            raise NotFoundError("administrator not found")
        permissions = await self._authorization.permission_codes(self._session, principal)
        return CurrentUserResponse(
            user=AdminUserBrief.model_validate(user),
            permissions=sorted(permissions),
            is_super_admin=bool(user.is_super_admin),
            must_change_password=bool(user.must_change_password),
            password_expired=is_password_expired(user.password_changed_at),
        )

    async def permissions(self, principal: Principal) -> PermissionsResponse:
        """Return the permission codes and the dynamic menu of the caller."""
        codes = await self._authorization.permission_codes(self._session, principal)
        resources = await self._authorization.visible_resources(
            self._session, principal, ("MENU", "PAGE", "BUTTON")
        )
        return PermissionsResponse(
            permissions=sorted(codes),
            menus=[MenuNode.model_validate(row) for row in resources],
            is_super_admin=principal.is_super_admin,
        )

    async def list_sessions(self, user_id: int) -> list[SessionBrief]:
        rows = await self._repository.list_active_sessions(user_id)
        return [SessionBrief.model_validate(row) for row in rows]

    # ------------------------------------------------------------------
    # Passwords
    # ------------------------------------------------------------------
    async def change_password(
        self,
        principal: Principal,
        *,
        old_password: str,
        new_password: str,
    ) -> None:
        """Change the caller's own password.

        Raises:
            AuthenticationError: when the current password is wrong.
            ValidationError: when the new password violates the policy.
            BusinessRuleError: when the new password repeats a recent one.
        """
        user = await self._repository.find_user_by_id(principal.subject_id)
        if user is None:
            raise NotFoundError("administrator not found")
        if not verify_password(old_password, str(user.password_hash)):
            await write_security_log(
                self._session,
                event_type="PASSWORD_CHANGE",
                result=RESULT_FAILURE,
                error_code="INVALID_PASSWORD",
                user_id=principal.subject_id,
                ip=principal.ip,
                user_agent=principal.user_agent,
            )
            await self._session.commit()
            raise AuthenticationError("current password is incorrect")

        await self._apply_new_password(user, new_password, actor=principal)

    async def reset_password(
        self,
        actor: Principal,
        *,
        user_id: int,
        reason: str | None = None,
    ) -> ResetPasswordResponse:
        """Reset another account's password and force a change on next login."""
        target = await self._repository.find_user_by_id(user_id)
        if target is None:
            raise NotFoundError("administrator not found")
        await self._authorization.assert_manageable_user(
            self._session,
            actor,
            target_user_id=int(target.id),
            target_department_id=target.department_id,
            target_is_super_admin=bool(target.is_super_admin),
            action="USER_RESET_PASSWORD",
        )
        temporary_password = generate_temporary_password(self._settings)
        await self._apply_new_password(
            target,
            temporary_password,
            actor=actor,
            force_change=True,
            audit_reason=reason,
        )
        return ResetPasswordResponse(
            user_id=str(int(target.id)),
            temporary_password=temporary_password,
            must_change_password=True,
        )

    async def _apply_new_password(
        self,
        user: SysUser,
        new_password: str,
        *,
        actor: Principal,
        force_change: bool = False,
        audit_reason: str | None = None,
    ) -> None:
        validate_password_policy(new_password, self._settings)
        history = await self._repository.recent_password_hashes(
            int(user.id), self._settings.PASSWORD_HISTORY_COUNT
        )
        for stored_hash in history:
            if verify_password(new_password, stored_hash):
                raise BusinessRuleError(
                    f"the password must differ from the last "
                    f"{self._settings.PASSWORD_HISTORY_COUNT} passwords"
                )

        now = datetime.datetime.now(datetime.UTC)
        before = {"password_changed_at": user.password_changed_at}
        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        user.password_expires_at = password_expiry_at(now, self._settings)
        user.must_change_password = force_change
        await self._repository.add_password_history(
            user_id=int(user.id), password_hash=str(user.password_hash)
        )
        await self._repository.trim_password_history(
            int(user.id), self._settings.PASSWORD_HISTORY_COUNT
        )
        await self._session.flush()

        await self._audit.record(
            self._session,
            action="USER_RESET_PASSWORD" if force_change else "PASSWORD_CHANGE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data={"password_changed_at": _iso(before["password_changed_at"])},
            after_data={"password_changed_at": _iso(now), "reason": audit_reason},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_security_log(
            self._session,
            event_type="PASSWORD_RESET" if force_change else "PASSWORD_CHANGE",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()


def _iso(value: datetime.datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def generate_temporary_password(settings: Settings | None = None) -> str:
    """Return a random password that satisfies the configured policy."""
    resolved = settings or get_settings()
    alphabet = string.ascii_letters + string.digits
    special = resolved.PASSWORD_SPECIAL_CHARACTERS or "!@#$%^&*"
    length = max(resolved.PASSWORD_MIN_LENGTH, 16)
    characters = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(special),
    ]
    characters += [secrets.choice(alphabet + special) for _ in range(length - len(characters))]
    secrets.SystemRandom().shuffle(characters)
    candidate = "".join(characters)
    validate_password_policy(candidate, resolved)
    return candidate


def token_pair_to_response(pair: TokenPair) -> TokenResponse:
    """Convert an issued pair into its DTO."""
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


def decode_subject(token: str) -> Any:
    """Decode an access token - exposed for session and trace tooling."""
    return decode_access_token(token)


def new_session_id() -> int:
    """Expose identifier generation for callers that build sessions directly."""
    return new_id()
