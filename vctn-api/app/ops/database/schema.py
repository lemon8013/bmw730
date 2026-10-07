"""app.ops.database — request and response DTOs.

Every collector reading shares the same degradation envelope: when the
PostgreSQL probe fails the metric fields stay ``None``, ``status`` becomes
``UNKNOWN`` and ``error`` carries the failure, so the monitoring page renders a
"collection failed" state instead of an HTTP 500.

Only structural data leaves this module. Statement texts coming from
``pg_stat_statements`` are already parameterised by PostgreSQL itself (literals
are replaced by placeholders), while ``pg_stat_activity.query`` — which does
hold raw user data — is never selected.
"""

from __future__ import annotations

import datetime
from typing import Final

from pydantic import Field

from app.shared.response.dto import ApiModel

STATUS_UP: Final[str] = "UP"
STATUS_UNKNOWN: Final[str] = "UNKNOWN"


class DatabaseProbeResult(ApiModel):
    """Degradation envelope shared by every PostgreSQL collector reading."""

    status: str
    collected_at: datetime.datetime
    error: str | None = None


class DatabaseOverviewResponse(DatabaseProbeResult):
    """Identity, liveness and headline numbers of the monitored instance."""

    version: str | None = None
    database_name: str | None = None
    uptime_seconds: float | None = None
    connection_count: int | None = None
    cache_hit_ratio: float | None = None
    database_size_bytes: int | None = None


class ConnectionStateCount(ApiModel):
    """Number of connections observed in one ``pg_stat_activity.state``."""

    state: str
    count: int


class DatabaseConnectionsResponse(DatabaseProbeResult):
    """Connection usage of the monitored database."""

    total: int | None = None
    max_connections: int | None = None
    utilization_ratio: float | None = None
    states: list[ConnectionStateCount] = Field(default_factory=list)


class DatabaseTransactionsResponse(DatabaseProbeResult):
    """Committed, rolled back and deadlocked transactions since statistics reset."""

    commits: int | None = None
    rollbacks: int | None = None
    deadlocks: int | None = None
    rollback_ratio: float | None = None


class WaitingSessionItem(ApiModel):
    """One session waiting on a lock, without its statement text."""

    pid: int
    database_name: str | None = None
    state: str | None = None
    wait_event_type: str | None = None
    wait_event: str | None = None
    wait_seconds: float | None = None


class DatabaseLocksResponse(DatabaseProbeResult):
    """Lock pressure of the monitored database."""

    total_locks: int | None = None
    granted_locks: int | None = None
    waiting_locks: int | None = None
    waiting_sessions: list[WaitingSessionItem] = Field(default_factory=list)


class SlowStatementItem(ApiModel):
    """One aggregated ``pg_stat_statements`` entry ranked by mean latency."""

    query_id: str | None = None
    calls: int | None = None
    rows: int | None = None
    total_ms: float | None = None
    mean_ms: float | None = None
    max_ms: float | None = None
    statement: str | None = None


class LongRunningQueryItem(ApiModel):
    """One currently executing query, described without its statement text."""

    pid: int
    database_name: str | None = None
    wait_event_type: str | None = None
    wait_event: str | None = None
    duration_seconds: float | None = None


class DatabaseSlowQueriesResponse(DatabaseProbeResult):
    """Slow-query statistics plus the sessions running longest right now.

    ``total_ms`` / ``mean_ms`` / ``max_ms`` are ``None`` while the
    ``pg_stat_statements`` extension is not installed; ``long_running_queries``
    stays available because ``pg_stat_activity`` needs no extension.
    """

    statements_extension_available: bool = False
    calls: int | None = None
    rows: int | None = None
    total_ms: float | None = None
    mean_ms: float | None = None
    max_ms: float | None = None
    slowest_statements: list[SlowStatementItem] = Field(default_factory=list)
    long_running_queries: list[LongRunningQueryItem] = Field(default_factory=list)


class TableStorageItem(ApiModel):
    """Storage footprint of one user table."""

    schema_name: str
    table_name: str
    total_bytes: int | None = None
    heap_bytes: int | None = None
    index_bytes: int | None = None
    live_rows: int | None = None


class DatabaseStorageResponse(DatabaseProbeResult):
    """Database-level storage usage and the largest user tables."""

    database_name: str | None = None
    database_size_bytes: int | None = None
    tables: list[TableStorageItem] = Field(default_factory=list)


class DatabaseCacheResponse(DatabaseProbeResult):
    """Buffer-cache efficiency of the monitored database."""

    blocks_hit: int | None = None
    blocks_read: int | None = None
    hit_ratio: float | None = None
