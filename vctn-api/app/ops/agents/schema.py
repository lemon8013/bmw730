"""app.ops.agents — request and response DTOs.

The plain agent token exists in exactly one DTO:
:class:`AgentRegisterResponse`, returned once by the registration endpoint.
Every other DTO carries only ``agent_code``, so a token can never reach a list
endpoint, a detail endpoint, an audit record or a log row.

The heartbeat request carries the credentials in optional fields: an agent may
either send them in the body or in the ``X-Agent-Code`` / ``X-Agent-Token``
headers, and the router merges the two before the service validates them.
"""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import METADATA_COLUMN_ALIAS, ApiModel, StringId

AGENT_STATUSES: frozenset[str] = frozenset({"ONLINE", "OFFLINE", "UPGRADING", "UNKNOWN"})

#: Status written when a heartbeat is accepted.
AGENT_STATUS_ONLINE: str = "ONLINE"

#: Host status written when a heartbeat of one of its agents is accepted.
HOST_STATUS_ONLINE: str = "ONLINE"

#: Window of the heartbeat history endpoint, in hours. The upper bound matches
#: the frozen retention of ``ops_metric_sample`` raw samples (7 days) with room
#: to spare, so a longer window can never be asked for and then answered empty.
DEFAULT_HEARTBEAT_WINDOW_HOURS: int = 24
MAX_HEARTBEAT_WINDOW_HOURS: int = 720

#: Metric keys a heartbeat projects into ``ops_metric_sample``.
METRIC_KEY_HOST_CPU_USAGE: str = "host.cpu_usage"
METRIC_KEY_HOST_MEMORY_USAGE: str = "host.memory_usage"
METRIC_KEY_HOST_DISK_USAGE: str = "host.disk_usage"


class AgentCreateRequest(ApiModel):
    """Register a collection agent."""

    agent_code: str
    agent_name: str
    host_id: str | None = None
    version: str | None = None
    metadata: dict | None = Field(default=None, validation_alias=METADATA_COLUMN_ALIAS)


class AgentResponse(ApiModel):
    """A registered collection agent.

    ``token_hash`` is deliberately absent: the hash must never be readable
    through the API.
    """

    id: StringId
    agent_code: str
    agent_name: str
    host_id: StringId | None = None
    version: str | None = None
    ip_address: str | None = None
    status: str
    enabled: bool
    last_heartbeat_at: datetime.datetime | None = None
    registered_at: datetime.datetime | None = None
    metadata: dict | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AgentRegisterResponse(AgentResponse):
    """A registered agent plus the plain token, returned exactly once.

    The token is not persisted anywhere, so this response is the only chance a
    caller has to store it.
    """

    token: str


class AgentHeartbeatRequest(ApiModel):
    """One heartbeat payload reported by an agent."""

    agent_code: str | None = None
    token: str | None = None
    version: str | None = None
    ip_address: str | None = None
    cpu_usage: float | None = None
    memory_usage: float | None = None
    disk_usage: float | None = None
    load1: float | None = None
    load5: float | None = None
    load15: float | None = None
    net_rx_bytes: int | None = None
    net_tx_bytes: int | None = None
    uptime_seconds: int | None = None
    collected_at: datetime.datetime | None = None


class AgentHeartbeatAcceptedResponse(ApiModel):
    """The result of one accepted heartbeat."""

    agent_id: StringId
    agent_code: str
    status: str
    collected_at: datetime.datetime
    metric_keys: list[str] = Field(default_factory=list)


class AgentHeartbeatResponse(ApiModel):
    """A stored heartbeat."""

    id: StringId
    agent_id: StringId
    cpu_usage: float | None = None
    memory_usage: float | None = None
    disk_usage: float | None = None
    load1: float | None = None
    load5: float | None = None
    load15: float | None = None
    net_rx_bytes: int | None = None
    net_tx_bytes: int | None = None
    uptime_seconds: int | None = None
    collected_at: datetime.datetime
    created_at: datetime.datetime
