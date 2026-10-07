"""app.ops.redis — business logic.

A read failure is data, not an error: an unreachable or unconfigured Redis is
reported as a structured degraded reading (``status='UNKNOWN'`` plus ``error``)
so the monitoring page stays up.

The service owns every derived number (hit ratio, memory and client
utilisation); the repository hands over parsed ``INFO`` sections only.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import Settings, get_settings
from app.ops.redis.repository import CLIENTS_SECTION, MEMORY_SECTION, RedisMonitorRepository
from app.ops.redis.schema import (
    STATUS_UNKNOWN,
    STATUS_UP,
    RedisClientsResponse,
    RedisKeyspaceItem,
    RedisKeyspaceResponse,
    RedisMemoryResponse,
    RedisOverviewResponse,
)

_LOGGER: logging.Logger = logging.getLogger("vctn.ops.redis")

#: A collector failure is reported in full detail; only its length is bounded so
#: that a pathological driver message cannot flood the response.
_MAX_ERROR_LENGTH = 500

_REDACTED = "<redacted>"


class RedisMonitorService:
    """Reads Redis health and performance counters."""

    def __init__(self, redis: aioredis.Redis | None, settings: Settings | None = None) -> None:
        self._repository = RedisMonitorRepository(redis)
        self._settings = settings or get_settings()

    async def overview(self) -> RedisOverviewResponse:
        """Headline health, efficiency and slow-log counters."""
        try:
            await self._repository.ping()
            server = await self._repository.info()
            hits = _int(server, "keyspace_hits")
            misses = _int(server, "keyspace_misses")
            keyspace = await self._repository.keyspace()
            used_memory = _int(server, "used_memory")
            return RedisOverviewResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                version=_text(server, "redis_version"),
                mode=_text(server, "redis_mode"),
                role=_text(server, "role"),
                uptime_seconds=_int(server, "uptime_in_seconds"),
                connected_clients=_int(server, "connected_clients"),
                blocked_clients=_int(server, "blocked_clients"),
                instantaneous_ops_per_sec=_int(server, "instantaneous_ops_per_sec"),
                hits=hits,
                misses=misses,
                hit_ratio=_ratio(hits, _sum(hits, misses)),
                evicted_keys=_int(server, "evicted_keys"),
                expired_keys=_int(server, "expired_keys"),
                used_memory_bytes=used_memory,
                used_memory_human=_text(server, "used_memory_human"),
                total_keys=sum(int(item["keys"]) for item in keyspace),
                slowlog_length=await self._repository.slowlog_length(),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return self._degraded(RedisOverviewResponse, exc)

    async def keyspace(self) -> RedisKeyspaceResponse:
        """Key statistics of every database reported by ``INFO keyspace``."""
        try:
            databases = [
                RedisKeyspaceItem(
                    name=str(item["name"]),
                    keys=int(item["keys"]),
                    expires=int(item["expires"]),
                    avg_ttl=int(item["avg_ttl"]),
                )
                for item in await self._repository.keyspace()
            ]
            return RedisKeyspaceResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                databases=databases,
                total_keys=sum(item.keys for item in databases),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return self._degraded(RedisKeyspaceResponse, exc)

    async def memory(self) -> RedisMemoryResponse:
        """Memory usage and policy reported by ``INFO memory``."""
        try:
            payload = await self._repository.info(MEMORY_SECTION)
            used_memory = _int(payload, "used_memory")
            max_memory = _int(payload, "maxmemory")
            max_memory = max_memory or None
            return RedisMemoryResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                used_memory_bytes=used_memory,
                used_memory_human=_text(payload, "used_memory_human"),
                used_memory_peak_bytes=_int(payload, "used_memory_peak"),
                used_memory_peak_human=_text(payload, "used_memory_peak_human"),
                used_memory_rss_bytes=_int(payload, "used_memory_rss"),
                max_memory_bytes=max_memory,
                max_memory_policy=_text(payload, "maxmemory_policy"),
                fragmentation_ratio=_float(payload, "mem_fragmentation_ratio"),
                utilization_ratio=_ratio(used_memory, max_memory),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return self._degraded(RedisMemoryResponse, exc)

    async def clients(self) -> RedisClientsResponse:
        """Client connections reported by ``INFO clients``."""
        try:
            payload = await self._repository.info(CLIENTS_SECTION)
            connected = _int(payload, "connected_clients")
            # Redis scans clients lazily, so a freshly started instance reports
            # the largest buffers only after the next scan; the values stay None
            # until then instead of being faked.
            return RedisClientsResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                connected_clients=connected,
                blocked_clients=_int(payload, "blocked_clients"),
                max_clients=_int(payload, "maxclients"),
                input_buffer_bytes=_int(payload, "client_recent_max_input_buffer"),
                output_buffer_bytes=_int(payload, "client_recent_max_output_buffer"),
                utilization_ratio=_ratio(connected, _int(payload, "maxclients")),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return self._degraded(RedisClientsResponse, exc)

    def _degraded(self, response_type: Any, exc: Exception) -> Any:
        """Build the ``UNKNOWN`` response for a failed collector read."""
        message = self._describe(exc)
        _LOGGER.warning("redis collector failed: %s", message)
        return response_type(
            status=STATUS_UNKNOWN,
            collected_at=datetime.datetime.now(datetime.UTC),
            error=message,
        )

    def _describe(self, exc: Exception) -> str:
        """Describe a failure without ever echoing a connection secret."""
        rendered = f"{type(exc).__name__}: {exc}"
        url = self._settings.redis_url
        if url:
            rendered = rendered.replace(url, _REDACTED)
        return rendered[:_MAX_ERROR_LENGTH]


def _int(payload: dict[str, str], key: str) -> int | None:
    """Read an integer counter, or ``None`` when Redis does not report it."""
    raw = payload.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _float(payload: dict[str, str], key: str) -> float | None:
    raw = payload.get(key)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _text(payload: dict[str, str], key: str) -> str | None:
    return payload.get(key)


def _sum(*values: int | None) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(value or 0 for value in values)


def _ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator)
