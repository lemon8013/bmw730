"""app.ops.hosts — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class HostCreateRequest(ApiModel):
    """Register a host to be monitored."""

    hostname: str
    display_name: str | None = None
    ip_address: str | None = None
    os_type: str | None = None
    os_version: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    disk_total_gb: int | None = None
    environment: str = "PRODUCTION"
    host_group_id: str | None = None
    tags: dict | None = None


class HostUpdateRequest(ApiModel):
    """Update a monitored host."""

    display_name: str | None = None
    ip_address: str | None = None
    os_type: str | None = None
    os_version: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    disk_total_gb: int | None = None
    environment: str | None = None
    host_group_id: str | None = None
    status: str | None = None
    tags: dict | None = None


class HostResponse(ApiModel):
    """A monitored host."""

    id: StringId
    hostname: str
    display_name: str | None = None
    ip_address: str | None = None
    os_type: str | None = None
    os_version: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    disk_total_gb: int | None = None
    environment: str
    host_group_id: str | None = None
    agent_id: str | None = None
    status: str
    last_seen_at: datetime.datetime | None = None
    tags: dict | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class HostGroupResponse(ApiModel):
    """A host group."""

    id: StringId
    group_code: str
    group_name: str
    description: str | None = None
    sort_order: int


class EnvironmentResponse(ApiModel):
    """A deployment environment."""

    id: StringId
    env_code: str
    env_name: str
    description: str | None = None
    sort_order: int
