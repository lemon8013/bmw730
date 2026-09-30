"""Access / refresh token issuing and verification.

Access tokens are JWTs (PyJWT). Refresh tokens are opaque random strings whose
SHA-256 digest is what gets persisted: a database leak must never hand an
attacker a usable refresh token.

Permissions are deliberately **not** embedded in the access token. A permission
change therefore takes effect on the very next request, as the Spec requires,
instead of waiting for the token to expire.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal

import jwt
from jwt import PyJWTError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError

SubjectType = Literal["admin", "platform"]

_TOKEN_TYPE_ACCESS: Final[str] = "access"
_TOKEN_TYPE_REFRESH: Final[str] = "refresh"

_SUBJECT_CLAIM: Final[str] = "sub"
_SESSION_CLAIM: Final[str] = "sid"
_SUBJECT_TYPE_CLAIM: Final[str] = "styp"
_TOKEN_TYPE_CLAIM: Final[str] = "ttyp"
_TOKEN_ID_CLAIM: Final[str] = "jti"


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Issued credential pair returned to a client."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int


def hash_refresh_token(refresh_token: str) -> str:
    """Return the stored digest of a refresh token."""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def generate_refresh_token(settings: Settings | None = None) -> str:
    """Return a new opaque refresh token."""
    resolved = settings or get_settings()
    return secrets.token_urlsafe(resolved.AUTH_REFRESH_TOKEN_BYTES)


def _encode(
    *,
    settings: Settings,
    subject_id: int,
    session_id: int,
    subject_type: SubjectType,
    token_type: str,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    payload: dict[str, Any] = {
        _SUBJECT_CLAIM: str(subject_id),
        _SESSION_CLAIM: str(session_id),
        _SUBJECT_TYPE_CLAIM: subject_type,
        _TOKEN_TYPE_CLAIM: token_type,
        _TOKEN_ID_CLAIM: secrets.token_hex(8),
        "iss": settings.AUTH_ISSUER,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.resolved_jwt_secret, algorithm=settings.AUTH_JWT_ALGORITHM)
    return str(token)


def issue_token_pair(
    *,
    subject_id: int,
    session_id: int,
    subject_type: SubjectType,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> tuple[TokenPair, str, datetime, datetime]:
    """Issue an access/refresh pair.

    Returns the pair for the client, the refresh token digest to persist, the
    access token expiry and the refresh token expiry.
    """
    resolved = settings or get_settings()
    issued_at = now or datetime.now(tz=UTC)
    access_expires_at = issued_at + timedelta(seconds=resolved.AUTH_ACCESS_TOKEN_TTL_SECONDS)
    refresh_expires_at = issued_at + timedelta(seconds=resolved.AUTH_REFRESH_TOKEN_TTL_SECONDS)

    access_token = _encode(
        settings=resolved,
        subject_id=subject_id,
        session_id=session_id,
        subject_type=subject_type,
        token_type=_TOKEN_TYPE_ACCESS,
        issued_at=issued_at,
        expires_at=access_expires_at,
    )
    refresh_token = generate_refresh_token(resolved)

    pair = TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=resolved.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        refresh_expires_in=resolved.AUTH_REFRESH_TOKEN_TTL_SECONDS,
    )
    return pair, hash_refresh_token(refresh_token), access_expires_at, refresh_expires_at


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Decoded access token claims."""

    subject_id: int
    session_id: int
    subject_type: SubjectType


def decode_access_token(token: str, settings: Settings | None = None) -> AccessTokenClaims:
    """Decode and validate an access token.

    Raises:
        AuthenticationError: when the token is malformed, expired or is not an
            access token.
    """
    resolved = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            resolved.resolved_jwt_secret,
            algorithms=[resolved.AUTH_JWT_ALGORITHM],
            issuer=resolved.AUTH_ISSUER,
        )
    except PyJWTError as exc:
        raise AuthenticationError("invalid or expired access token") from exc

    if payload.get(_TOKEN_TYPE_CLAIM) != _TOKEN_TYPE_ACCESS:
        raise AuthenticationError("invalid or expired access token")

    subject_type = payload.get(_SUBJECT_TYPE_CLAIM)
    if subject_type not in ("admin", "platform"):
        raise AuthenticationError("invalid or expired access token")

    try:
        subject_id = int(str(payload[_SUBJECT_CLAIM]))
        session_id = int(str(payload[_SESSION_CLAIM]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("invalid or expired access token") from exc

    return AccessTokenClaims(
        subject_id=subject_id, session_id=session_id, subject_type=subject_type
    )


def constant_time_equals(left: str, right: str) -> bool:
    """Compare two strings without leaking their content through timing."""
    return hmac.compare_digest(left, right)
