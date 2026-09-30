"""app.platform.auth — business logic.

Registration and login only touch the business user's own tables; everything a
growth account, a point account, a task or an achievement needs is published as
an outbox event and applied by the owning module.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.platform.auth.repository import PlatformAuthRepository
from app.platform.auth.schema import (
    LoginResponse,
    PlatformSessionBrief,
    PlatformUserBrief,
    SendVerificationResponse,
    TokenResponse,
    VerifyResponse,
)
from app.platform.users.model import BizUser, BizUserSession
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.events.codes import OutboxEventType
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_FAILURE, RESULT_SUCCESS, write_security_log
from app.shared.outbox.service import OutboxService
from app.shared.rate_limit.service import RateLimitService
from app.shared.security.masking import mask_email, mask_phone
from app.shared.security.password import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.shared.security.tokens import (
    TokenPair,
    hash_refresh_token,
    issue_token_pair,
)

ACTIVE_STATUS: str = "ACTIVE"
LOCKED_STATUS: str = "LOCKED"
IDENTITY_USERNAME: str = "USERNAME"
IDENTITY_EMAIL: str = "EMAIL"
IDENTITY_PHONE: str = "PHONE"


class PlatformAuthService:
    """Business user registration, login, session and verification logic."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        redis: aioredis.Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._repository = PlatformAuthRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._outbox = OutboxService(self._settings)
        self._rate_limit = RateLimitService(redis, self._settings) if redis is not None else None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    async def register(
        self,
        *,
        username: str,
        password: str,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> BizUser:
        """Register a business user.

        Raises:
            ConflictError: when the username, email or phone is already taken.
            ValidationError: when the password violates the policy.
        """
        if self._rate_limit is not None:
            await self._rate_limit.enforce(
                bucket="register",
                subject=f"ip:{ip or 'unknown'}",
                limit=self._settings.RATE_LIMIT_SENSITIVE_PER_WINDOW,
            )
        if not (email or phone):
            raise ValidationError("either an email or a phone number is required")
        validate_password_policy(password, self._settings)

        if await self._repository.find_user_by_username(username) is not None:
            raise ConflictError("username is already taken")
        for identity_type, value in ((IDENTITY_EMAIL, email), (IDENTITY_PHONE, phone)):
            if value and await self._repository.find_identity(identity_type, value) is not None:
                raise ConflictError(f"{identity_type.lower()} is already registered")

        now = datetime.datetime.now(datetime.UTC)
        user = BizUser(
            id=new_id(),
            username=username,
            nickname=nickname or username,
            status=ACTIVE_STATUS,
            email=email,
            phone=phone,
            registered_at=now,
        )
        self._repository.add_user(user)
        await self._session.flush()

        await self._repository.add_identity(
            user_id=int(user.id),
            identity_type=IDENTITY_USERNAME,
            identity_value=username,
            verified=True,
        )
        if email:
            await self._repository.add_identity(
                user_id=int(user.id),
                identity_type=IDENTITY_EMAIL,
                identity_value=email,
                verified=False,
            )
        if phone:
            await self._repository.add_identity(
                user_id=int(user.id),
                identity_type=IDENTITY_PHONE,
                identity_value=phone,
                verified=False,
            )
        await self._repository.add_password_history(
            user_id=int(user.id), password_hash=hash_password(password)
        )
        await self._repository.trim_password_history(
            int(user.id), self._settings.PASSWORD_HISTORY_COUNT
        )

        await self._outbox.publish(
            self._session,
            event_type=OutboxEventType.USER_REGISTERED,
            aggregate_type="biz_user",
            aggregate_id=int(user.id),
            payload={"user_id": int(user.id), "occurred_at": now.isoformat()},
        )
        await write_security_log(
            self._session,
            event_type="USER_REGISTER",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        await self._audit.record(
            self._session,
            action="PLATFORM_REGISTER",
            resource_type="biz_user",
            resource_id=int(user.id),
            after_data={"username": user.username},
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
        return user

    # ------------------------------------------------------------------
    # Login / session
    # ------------------------------------------------------------------
    async def login(
        self,
        *,
        identity: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
        device_type: str | None = None,
        anonymous_id: str | None = None,
    ) -> LoginResponse:
        """Authenticate a business user by username, email or phone."""
        if self._rate_limit is not None:
            await self._rate_limit.enforce(
                bucket="login",
                subject=f"platform:{identity.lower()}",
                limit=self._settings.RATE_LIMIT_LOGIN_PER_WINDOW,
            )

        user = await self._resolve_by_identity(identity)
        now = datetime.datetime.now(datetime.UTC)
        if user is None:
            await self._fail_login(
                user_id=None,
                identity=identity,
                failure_code="IDENTITY_NOT_FOUND",
                ip=ip,
                user_agent=user_agent,
            )
            raise AuthenticationError("invalid identity or password")
        if str(user.status) == LOCKED_STATUS:
            await self._fail_login(
                user_id=int(user.id),
                identity=identity,
                failure_code="ACCOUNT_LOCKED",
                ip=ip,
                user_agent=user_agent,
            )
            raise AuthenticationError("account is locked")
        if await self._is_brute_force_locked(user, now=now):
            await self._fail_login(
                user_id=int(user.id),
                identity=identity,
                failure_code="ACCOUNT_LOCKED",
                ip=ip,
                user_agent=user_agent,
            )
            raise AuthenticationError("too many failed attempts, please retry later")
        if not verify_password(password, await self._current_password_hash(int(user.id))):
            await self._fail_login(
                user_id=int(user.id),
                identity=identity,
                failure_code="INVALID_PASSWORD",
                ip=ip,
                user_agent=user_agent,
            )
            raise AuthenticationError("invalid identity or password")

        user.last_login_at = now
        await self._session.flush()

        await self._enforce_session_limit(user, now=now)
        session_row = await self._repository.create_session(
            user_id=int(user.id),
            refresh_token_hash="pending",
            anonymous_id_hash=hash_anonymous_id(anonymous_id) if anonymous_id else None,
            ip=ip,
            user_agent=user_agent,
            device_type=device_type,
            login_at=now,
            expires_at=now
            + datetime.timedelta(seconds=self._settings.AUTH_REFRESH_TOKEN_TTL_SECONDS),
        )
        pair, digest, _, _ = issue_token_pair(
            subject_id=int(user.id),
            session_id=int(session_row.id),
            subject_type="platform",
            now=now,
            settings=self._settings,
        )
        session_row.refresh_token_hash = digest
        await self._session.flush()

        await self._repository.add_login_log(
            id=new_id(),
            user_id=int(user.id),
            identity_type=_identity_kind(identity),
            success=True,
            ip=ip,
            user_agent=user_agent,
            anonymous_id_hash=hash_anonymous_id(anonymous_id) if anonymous_id else None,
            occurred_at=now,
        )
        await self._outbox.publish(
            self._session,
            event_type=OutboxEventType.USER_LOGGED_IN,
            aggregate_type="biz_user",
            aggregate_id=int(user.id),
            payload={
                "user_id": int(user.id),
                "stat_date": now.date().isoformat(),
                "occurred_at": now.isoformat(),
            },
        )
        await write_security_log(
            self._session,
            event_type="USER_LOGIN",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
        return LoginResponse(
            token=TokenResponse(
                access_token=pair.access_token,
                refresh_token=pair.refresh_token,
                token_type=pair.token_type,
                expires_in=pair.expires_in,
                refresh_expires_in=pair.refresh_expires_in,
            ),
            user_id=str(int(user.id)),
            nickname=user.nickname,
        )

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        """Rotate the refresh token of a business user session."""
        digest = hash_refresh_token(refresh_token)
        session_row = await self._repository.find_session_by_refresh_hash(digest)
        now = datetime.datetime.now(datetime.UTC)
        if (
            session_row is None
            or session_row.revoked_at is not None
            or str(session_row.session_status) != "ACTIVE"
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

        user = await self._repository.find_user(int(session_row.user_id))
        if user is None or str(user.status) != ACTIVE_STATUS:
            raise AuthenticationError("account is not active")

        pair, new_digest, _, _ = issue_token_pair(
            subject_id=int(user.id),
            session_id=int(session_row.id),
            subject_type="platform",
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
        """Revoke the caller's session."""
        revoked = await self._repository.revoke_sessions(
            [principal.session_id], reason=reason, revoked_at=datetime.datetime.now(datetime.UTC)
        )
        await write_security_log(
            self._session,
            event_type="USER_LOGOUT",
            result=RESULT_SUCCESS if revoked else RESULT_FAILURE,
            error_code=None if revoked else "SESSION_NOT_FOUND",
            user_id=principal.subject_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()

    async def change_password(
        self, principal: Principal, *, old_password: str, new_password: str
    ) -> None:
        """Change the password of the signed in business user."""
        user = await self._repository.find_user(principal.subject_id)
        if user is None:
            raise NotFoundError("user not found")
        if not verify_password(old_password, await self._current_password_hash(int(user.id))):
            await write_security_log(
                self._session,
                event_type="PASSWORD_CHANGE",
                result=RESULT_FAILURE,
                error_code="INVALID_PASSWORD",
                user_id=int(user.id),
                ip=principal.ip,
                user_agent=principal.user_agent,
            )
            await self._session.commit()
            raise AuthenticationError("current password is incorrect")

        validate_password_policy(new_password, self._settings)
        history = await self._repository.recent_password_hashes(
            int(user.id), self._settings.PASSWORD_HISTORY_COUNT
        )
        for stored in history:
            if verify_password(new_password, stored):
                raise BusinessRuleError(
                    f"the password must differ from the last "
                    f"{self._settings.PASSWORD_HISTORY_COUNT} passwords"
                )
        await self._repository.add_password_history(
            user_id=int(user.id), password_hash=hash_password(new_password)
        )
        await self._repository.trim_password_history(
            int(user.id), self._settings.PASSWORD_HISTORY_COUNT
        )
        await write_security_log(
            self._session,
            event_type="PASSWORD_CHANGE",
            result=RESULT_SUCCESS,
            user_id=int(user.id),
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()

    async def current_user(self, user_id: int) -> BizUser:
        """Return the signed in business user."""
        user = await self._repository.find_user(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user

    async def list_sessions(self, principal: Principal) -> list[PlatformSessionBrief]:
        rows = await self._repository.list_active_sessions(principal.subject_id)
        return [
            PlatformSessionBrief(
                id=str(int(row.id)),
                session_status=str(row.session_status),
                device_type=row.device_type,
                login_at=row.login_at,
                last_active_at=row.last_active_at,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
                revoke_reason=row.revoke_reason,
                ip=None if row.ip is None else str(row.ip),
            )
            for row in rows
        ]

    async def revoke_session(self, principal: Principal, session_id: int) -> None:
        """Revoke one of the caller's own sessions."""
        owned = {
            int(row.id) for row in await self._repository.list_active_sessions(principal.subject_id)
        }
        if session_id not in owned:
            await self._audit.record_failure(
                self._session,
                action="PLATFORM_SESSION_REVOKE",
                error_code="SESSION_NOT_OWNED",
                operator_id=principal.subject_id,
                resource_type="biz_user_session",
                resource_id=session_id,
                ip=principal.ip,
                user_agent=principal.user_agent,
            )
            await self._session.commit()
            raise NotFoundError("session not found")
        await self._repository.revoke_sessions(
            [session_id], reason="USER_REVOKED", revoked_at=datetime.datetime.now(datetime.UTC)
        )
        await write_security_log(
            self._session,
            event_type="SESSION_REVOKE",
            result=RESULT_SUCCESS,
            user_id=principal.subject_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    async def send_verification(
        self,
        *,
        verification_type: str,
        target: str,
        user_id: int | None = None,
        ip: str | None = None,
    ) -> SendVerificationResponse:
        """Create a verification challenge for an email address or phone number.

        No notification provider is frozen, so the response reports
        ``delivery = NONE`` instead of claiming a message was sent.
        """
        if self._rate_limit is not None:
            await self._rate_limit.enforce(
                bucket="verification",
                subject=f"{ip or 'unknown'}:{target.lower()}",
                limit=self._settings.RATE_LIMIT_SENSITIVE_PER_WINDOW,
            )
        code = "".join(
            secrets.choice("0123456789") for _ in range(self._settings.VERIFICATION_CODE_LENGTH)
        )
        now = datetime.datetime.now(datetime.UTC)
        expires_at = now + datetime.timedelta(seconds=self._settings.VERIFICATION_CODE_TTL_SECONDS)
        row = await self._repository.add_verification(
            id=new_id(),
            user_id=user_id,
            verification_type=verification_type,
            target_hash=hash_target(target),
            code_hash=hash_target(code),
            expires_at=expires_at,
            attempt_count=0,
        )
        await self._audit.record(
            self._session,
            action="PLATFORM_SEND_VERIFICATION",
            operator_id=user_id,
            resource_type="biz_user_verification",
            resource_id=int(row.id),
            after_data={"verification_type": verification_type, "delivery": "NONE"},
            ip=ip,
        )
        await self._session.commit()
        masked = mask_email(target) if verification_type == "EMAIL" else mask_phone(target)
        return SendVerificationResponse(
            verification_id=str(int(row.id)),
            verification_type=verification_type,
            target_masked=str(masked),
            expires_at=expires_at,
            delivery="NONE",
            debug_code=code if self._settings.APP_ENV in ("development", "testing") else None,
        )

    async def verify(
        self, *, verification_id: int, code: str, user_id: int | None = None
    ) -> VerifyResponse:
        """Consume a verification code."""
        row = await self._repository.get_verification(verification_id)
        if row is None:
            raise NotFoundError("verification not found")
        now = datetime.datetime.now(datetime.UTC)
        if row.consumed_at is not None:
            raise ConflictError("the verification code was already used")
        if row.expires_at <= now:
            raise BusinessRuleError("the verification code has expired")
        attempts = int(row.attempt_count or 0) + 1
        row.attempt_count = attempts
        if attempts > self._settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            await self._session.flush()
            await self._session.commit()
            raise BusinessRuleError("too many verification attempts")
        if not secrets.compare_digest(str(row.code_hash), hash_target(code)):
            await self._session.flush()
            await self._session.commit()
            raise ValidationError("the verification code is incorrect")

        row.consumed_at = now
        identity_type = "EMAIL" if str(row.verification_type) == "EMAIL" else "PHONE"
        if row.user_id is not None:
            await self._repository.mark_identity_verified(
                user_id=int(row.user_id), identity_type=identity_type
            )
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="PLATFORM_VERIFY",
            operator_id=user_id if user_id is not None else row.user_id,
            resource_type="biz_user_verification",
            resource_id=verification_id,
            after_data={"identity_type": identity_type},
        )
        await self._session.commit()
        return VerifyResponse(
            verification_id=str(verification_id), verified=True, identity_type=identity_type
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _resolve_by_identity(self, identity: str) -> BizUser | None:
        for identity_type in (IDENTITY_USERNAME, IDENTITY_EMAIL, IDENTITY_PHONE):
            row = await self._repository.find_identity(identity_type, identity)
            if row is not None:
                return await self._repository.find_user(int(row.user_id))
        return await self._repository.find_user_by_username(identity)

    async def _current_password_hash(self, user_id: int) -> str:
        history = await self._repository.recent_password_hashes(user_id, 1)
        if not history:
            raise AuthenticationError("account has no password set")
        return history[0]

    async def _is_brute_force_locked(self, user: BizUser, *, now: datetime.datetime) -> bool:
        """Return whether too many failures happened inside the lock window."""
        window_start = now - datetime.timedelta(minutes=self._settings.PASSWORD_LOCK_MINUTES)
        failures = await self._repository.count_recent_failures(int(user.id), since=window_start)
        return failures >= self._settings.PASSWORD_MAX_FAILED_ATTEMPTS

    async def _fail_login(
        self,
        *,
        user_id: int | None,
        identity: str,
        failure_code: str,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        now = datetime.datetime.now(datetime.UTC)
        await self._repository.add_login_log(
            id=new_id(),
            user_id=user_id,
            identity_type=_identity_kind(identity),
            success=False,
            failure_code=failure_code,
            ip=ip,
            user_agent=user_agent,
            occurred_at=now,
        )
        await write_security_log(
            self._session,
            event_type="USER_LOGIN",
            result=RESULT_FAILURE,
            error_code=failure_code,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()

    async def _enforce_session_limit(self, user: BizUser, *, now: datetime.datetime) -> None:
        limit = self._settings.AUTH_MAX_ACTIVE_SESSIONS_PER_USER
        stale = await self._repository.oldest_active_session_ids(int(user.id), max(0, limit - 1))
        if stale:
            await self._repository.revoke_sessions(stale, reason="SESSION_LIMIT", revoked_at=now)


def _identity_kind(identity: str) -> str:
    if "@" in identity:
        return IDENTITY_EMAIL
    if identity.isdigit():
        return IDENTITY_PHONE
    return IDENTITY_USERNAME


def hash_target(value: str) -> str:
    """Return the stored digest of a verification target or code."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def hash_anonymous_id(anonymous_id: str) -> str:
    """Return the stored digest of a guest identifier."""
    return hashlib.sha256(anonymous_id.strip().encode("utf-8")).hexdigest()


def to_user_brief(user: BizUser) -> PlatformUserBrief:
    """Render a business user as its DTO."""
    return PlatformUserBrief(
        id=str(int(user.id)),
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        phone=user.phone,
        avatar_url=user.avatar_url,
        status=str(user.status),
        registered_at=user.registered_at,
        last_login_at=user.last_login_at,
    )


def token_response(pair: TokenPair) -> TokenResponse:
    """Render an issued pair as its DTO."""
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


def session_brief(row: BizUserSession) -> dict[str, Any]:
    """Render one session row as a plain mapping."""
    return {
        "id": str(int(row.id)),
        "session_status": row.session_status,
        "device_type": row.device_type,
        "login_at": row.login_at,
        "last_active_at": row.last_active_at,
        "expires_at": row.expires_at,
        "revoked_at": row.revoked_at,
        "revoke_reason": row.revoke_reason,
    }
