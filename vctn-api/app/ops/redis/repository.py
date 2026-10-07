"""app.ops.redis — read-only Redis introspection.

The client comes from :func:`app.shared.redis.client.build_redis` and only
read-only informational commands are issued: ``PING``, ``INFO`` and
``SLOWLOG LEN``. No key-value command exists here at all — no ``KEYS``,
``SCAN``-driven browsing, ``GET``/``SET``/``DEL``, and certainly no ``FLUSH`` —
so there is no Redis console to abuse.

The repository never interprets a counter beyond parsing it: derived numbers
(hit ratios, utilisation) belong to the service.
"""

from __future__ import annotations

from typing import Any, Final

import redis.asyncio as aioredis

from app.core.exceptions import ServiceUnavailableError

KEYSPACE_SECTION: Final[str] = "keyspace"
MEMORY_SECTION: Final[str] = "memory"
CLIENTS_SECTION: Final[str] = "clients"


def _decode(value: Any) -> str:
    """Render an ``INFO`` value as text whether or not the client decodes it."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _parse_counter(payload: dict[str, str], key: str, target: str) -> int:
    """Read one ``key=value`` counter out of a comma separated ``INFO`` value."""
    for part in payload[key].split(","):
        name, separator, raw = part.partition("=")
        if separator and name.strip() == target:
            try:
                return int(raw.strip())
            except ValueError:
                return 0
    return 0


class RedisMonitorRepository:
    """Executes the fixed read-only Redis introspection commands."""

    def __init__(self, client: aioredis.Redis | None) -> None:
        self._client = client

    def _require_client(self) -> aioredis.Redis:
        if self._client is None:
            raise ServiceUnavailableError("redis is not configured")
        return self._client

    async def ping(self) -> None:
        """Fail when Redis is unreachable."""
        await self._require_client().ping()

    async def info(self, section: str | None = None) -> dict[str, str]:
        """Return one ``INFO`` section as a flat mapping."""
        client = self._require_client()
        payload = await (client.info(section) if section else client.info())
        return {_decode(key): _decode(value) for key, value in dict(payload).items()}

    async def slowlog_length(self) -> int:
        """Return the number of entries currently held by the slow log."""
        return int(await self._require_client().slowlog_len())

    async def keyspace(self) -> list[dict[str, Any]]:
        """Return per-database key statistics parsed out of ``INFO keyspace``."""
        payload = await self.info(KEYSPACE_SECTION)
        databases: list[dict[str, Any]] = []
        for key in sorted(name for name in payload if name.startswith("db")):
            databases.append(
                {
                    "name": key,
                    "keys": _parse_counter(payload, key, "keys"),
                    "expires": _parse_counter(payload, key, "expires"),
                    "avg_ttl": _parse_counter(payload, key, "avg_ttl"),
                }
            )
        return databases
