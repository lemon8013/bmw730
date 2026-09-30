"""Password hashing and the frozen password policy.

Policy (frozen):

* minimum 12 characters
* at least one uppercase letter, one lowercase letter, one digit and one
  special character
* the last 5 passwords may not be reused
* a password expires 90 days after it was last changed
* 5 consecutive failed logins lock the account for 30 minutes

Which character counts as "special", how long the history is and how long a lock
lasts are configuration, read from :class:`app.core.config.Settings`.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from pwdlib import PasswordHash

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

_PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(raw_password: str) -> str:
    """Hash a plain text password. The plain text is never stored or logged."""
    return _PASSWORD_HASHER.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Return whether ``raw_password`` matches ``password_hash``."""
    try:
        return _PASSWORD_HASHER.verify(raw_password, password_hash)
    except ValueError:
        # An unparsable stored hash is a failed verification, never a crash.
        return False


def validate_password_policy(raw_password: str, settings: Settings | None = None) -> None:
    """Raise :class:`ValidationError` when the password violates the policy.

    The rejected reason is reported through the exception ``data`` payload. The
    password itself is never included.
    """
    resolved = settings or get_settings()
    problems: list[str] = []

    if len(raw_password) < resolved.PASSWORD_MIN_LENGTH:
        problems.append(f"password must be at least {resolved.PASSWORD_MIN_LENGTH} characters")
    if resolved.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", raw_password):
        problems.append("password must contain an uppercase letter")
    if resolved.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", raw_password):
        problems.append("password must contain a lowercase letter")
    if resolved.PASSWORD_REQUIRE_DIGIT and not re.search(r"[0-9]", raw_password):
        problems.append("password must contain a digit")
    if resolved.PASSWORD_REQUIRE_SPECIAL:
        special = set(resolved.PASSWORD_SPECIAL_CHARACTERS)
        if not any(character in special for character in raw_password):
            problems.append("password must contain a special character")

    if problems:
        raise ValidationError("password does not satisfy the password policy", data=problems)


def is_password_expired(
    password_changed_at: datetime | None,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> bool:
    """Return whether a password outlived ``PASSWORD_EXPIRE_DAYS``.

    A password that was never changed (``None``) is not treated as expired: the
    account creation flow always writes ``password_changed_at``.
    """
    if password_changed_at is None:
        return False
    resolved = settings or get_settings()
    reference = now or datetime.now(tz=password_changed_at.tzinfo)
    return password_changed_at + timedelta(days=resolved.PASSWORD_EXPIRE_DAYS) <= reference


def password_expiry_at(password_changed_at: datetime, settings: Settings | None = None) -> datetime:
    """Return the instant at which the current password expires."""
    resolved = settings or get_settings()
    return password_changed_at + timedelta(days=resolved.PASSWORD_EXPIRE_DAYS)


def lock_until_after_failures(now: datetime, settings: Settings | None = None) -> datetime:
    """Return the instant at which an account locked by failures unlocks."""
    resolved = settings or get_settings()
    return now + timedelta(minutes=resolved.PASSWORD_LOCK_MINUTES)


def build_policy_description(settings: Settings | None = None) -> dict[str, object]:
    """Return the policy as it is currently configured."""
    resolved = settings or get_settings()
    return {
        "min_length": resolved.PASSWORD_MIN_LENGTH,
        "require_uppercase": resolved.PASSWORD_REQUIRE_UPPERCASE,
        "require_lowercase": resolved.PASSWORD_REQUIRE_LOWERCASE,
        "require_digit": resolved.PASSWORD_REQUIRE_DIGIT,
        "require_special": resolved.PASSWORD_REQUIRE_SPECIAL,
        "history_count": resolved.PASSWORD_HISTORY_COUNT,
        "expire_days": resolved.PASSWORD_EXPIRE_DAYS,
        "max_failed_attempts": resolved.PASSWORD_MAX_FAILED_ATTEMPTS,
        "lock_minutes": resolved.PASSWORD_LOCK_MINUTES,
    }
