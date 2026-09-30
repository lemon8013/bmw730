"""Sensitive data masking.

Every value that reaches a log line, an audit record, a security log, an
operation log or an access log passes through this module first.
"""

from __future__ import annotations

_TOKEN_VISIBLE_PREFIX = 6
_PHONE_HEAD = 3
_PHONE_TAIL = 4
_EMAIL_HEAD = 3

_REDACTED = "***"


def mask_phone(value: str | None) -> str | None:
    """``13812341234`` becomes ``138****1234``."""
    if not value:
        return value
    if len(value) <= _PHONE_HEAD + _PHONE_TAIL:
        return value[0] + _REDACTED
    return f"{value[:_PHONE_HEAD]}****{value[-_PHONE_TAIL:]}"


def mask_email(value: str | None) -> str | None:
    """``abcdef@example.com`` becomes ``abc***@example.com``."""
    if not value:
        return value
    local, separator, domain = value.partition("@")
    if not separator:
        return (local[:_EMAIL_HEAD] + _REDACTED) if local else value
    return f"{local[:_EMAIL_HEAD]}***@{domain}"


def mask_token(value: str | None) -> str | None:
    """Keep at most the first six characters of a token."""
    if not value:
        return value
    if len(value) <= _TOKEN_VISIBLE_PREFIX:
        return _REDACTED
    return f"{value[:_TOKEN_VISIBLE_PREFIX]}..."


def mask_secret(_: str | None) -> str:
    """Secrets (password, MFA secret, API key) are never rendered at all."""
    return _REDACTED


def mask_mapping(values: dict[str, object]) -> dict[str, object]:
    """Mask the well known sensitive keys of a payload.

    Unknown keys are kept as they are: masking must never silently drop the
    context an operator needs to understand a record. Field level policies are
    enforced elsewhere, by the authorization layer.
    """
    masked: dict[str, object] = {}
    for key, value in values.items():
        lowered = key.lower()
        if lowered in {"password", "new_password", "old_password", "confirm_password"}:
            masked[key] = mask_secret(str(value)) if value is not None else None
        elif lowered in {"mfa_secret", "secret", "api_key", "apikey", "client_secret"}:
            masked[key] = mask_secret(str(value)) if value is not None else None
        elif "token" in lowered or lowered == "authorization":
            masked[key] = mask_token(str(value)) if value is not None else None
        elif lowered in {"phone", "mobile", "telephone"}:
            masked[key] = mask_phone(str(value)) if value is not None else None
        elif lowered in {"email", "mail"}:
            masked[key] = mask_email(str(value)) if value is not None else None
        else:
            masked[key] = value
    return masked
