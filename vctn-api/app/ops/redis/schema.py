"""app.ops.redis — request and response DTOs.

Like the PostgreSQL collector, every Redis reading shares one degradation
envelope: when the cache is unreachable or not configured the metric fields stay
``None``, ``status`` becomes ``UNKNOWN`` and ``error`` explains why, so the
monitoring page renders a "collection failed" state instead of an HTTP 500.

Only ``INFO`` counters selected by name are exposed; the raw ``INFO`` dump is
never echoed back.
"""

from __future__ import annotations

import datetime
from typing import Final

from pydantic import Field

from app.shared.response.dto import ApiModel

STATUS_UP: Final[str] = "UP"
STATUS_UNKNOWN: Final[str] = "UNKNOWN"


class RedisProbeResult(ApiModel):
    """Degradation envelope shared by every Redis collector reading."""

    status: str
    collected_at: datetime.datetime
    error: str | None = None


class RedisOverviewResponse(RedisProbeResult):
    """Headline health and efficiency counters of the monitored cache."""

    version: str | None = None
    mode: str | None = None
    role: str | None = None
    uptime_seconds: int | None = None
    connected_clients: int | None = None
    blocked_clients: int | None = None
    instantaneous_ops_per_sec: int | None = None
    hits: int | None = None
    misses: int | None = None
    hit_ratio: float | None = None
    evicted_keys: int | None = None
    expired_keys: int | None = None
    used_memory_bytes: int | None = None
    used_memory_human: str | None = None
    total_keys: int | None = None
    slowlog_length: int | None = None


class RedisKeyspaceItem(ApiModel):
    """Per-database key statistics reported by ``INFO keyspace``."""

    name: str
    keys: int
    expires: int | None = None
    avg_ttl: int | None = None


class RedisKeyspaceResponse(RedisProbeResult):
    """Key statistics of every database that currently holds keys."""

    databases: list[RedisKeyspaceItem] = Field(default_factory=list)
    total_keys: int = 0


class RedisMemoryResponse(RedisProbeResult):
    """Memory usage reported by ``INFO memory``."""

    used_memory_bytes: int | None = None
    used_memory_human: str | None = None
    used_memory_peak_bytes: int | None = None
    used_memory_peak_human: str | None = None
    used_memory_rss_bytes: int | None = None
    max_memory_bytes: int | None = None
    max_memory_policy: str | None = None
    fragmentation_ratio: float | None = None
    utilization_ratio: float | None = None


class RedisClientsResponse(RedisProbeResult):
    """Client connections reported by ``INFO clients``."""

    connected_clients: int | None = None
    blocked_clients: int | None = None
    max_clients: int | None = None
    input_buffer_bytes: int | None = None
    output_buffer_bytes: int | None = None
    utilization_ratio: float | None = None
