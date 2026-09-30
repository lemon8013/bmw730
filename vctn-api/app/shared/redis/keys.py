"""Redis key naming.

Keys are namespaced by ``REDIS_KEY_PREFIX`` so several environments can share
one Redis instance. Exact TTLs are not frozen by the Spec, therefore every TTL
used here is either passed by the caller or read from configuration.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings


def build_key(settings: Settings | None, *parts: str) -> str:
    """Return ``prefix:part:part``."""
    resolved = settings or get_settings()
    return ":".join((resolved.REDIS_KEY_PREFIX, *parts))


def rate_limit_key(*, bucket: str, subject: str) -> str:
    return build_key(None, "ratelimit", bucket, subject)


def lock_key(*, name: str) -> str:
    return build_key(None, "lock", name)


def quota_key(*, subject: str, tool_id: int, stat_date: str) -> str:
    return build_key(None, "quota", subject, str(tool_id), stat_date)


def session_key(*, subject_type: str, subject_id: int) -> str:
    return build_key(None, "session", subject_type, str(subject_id))
