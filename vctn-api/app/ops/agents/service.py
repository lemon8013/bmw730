"""app.ops.agents — business logic.

The service owns the transaction: every operator mutation commits at the end and
writes an audit record plus an operation log.

Credential handling is the one rule that shapes this module: the plain token is
generated here, returned once to the caller, hashed with ``sha256`` and then
discarded. It is never persisted, never logged and never audited — only
``agent_code`` reaches the audit trail.

A heartbeat is the exception to the audit rule: it is reported by the agent
itself, so there is no :class:`Principal` to attribute it to, and
:class:`OpsAuditRecorder` refuses to invent an operator. The heartbeat is
therefore traced through the operation log only, and its own row in
``ops_agent_heartbeat`` is the authoritative record of what was reported.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.ops.agents.model import OpsAgent, OpsAgentHeartbeat
from app.ops.agents.repository import AgentRepository
from app.ops.agents.schema import (
    AGENT_STATUS_ONLINE,
    HOST_STATUS_ONLINE,
    METRIC_KEY_HOST_CPU_USAGE,
    METRIC_KEY_HOST_DISK_USAGE,
    METRIC_KEY_HOST_MEMORY_USAGE,
    AgentCreateRequest,
    AgentHeartbeatAcceptedResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegisterResponse,
    AgentResponse,
)
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.hosts.model import OpsHost
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

#: Entropy of a generated agent token, in bytes.
AGENT_TOKEN_BYTES: int = 32

#: Fallback environment of a sample whose agent is not bound to a host.
DEFAULT_ENVIRONMENT: str = "PRODUCTION"

#: Status written when an agent is disabled: it stops reporting, so it is off.
AGENT_STATUS_OFFLINE: str = "OFFLINE"


class AgentService:
    """Agent registration, enablement and heartbeat ingestion."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AgentRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_agents(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        enabled: bool | None = None,
        page: PageParams,
    ) -> Page[AgentResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            status=status,
            enabled=enabled,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_agent(self, agent_id: int) -> AgentResponse:
        row = await self._repository.get(agent_id)
        if row is None:
            raise NotFoundError("agent not found")
        return self._to_response(row)

    async def register_agent(
        self, actor: Principal, payload: AgentCreateRequest
    ) -> AgentRegisterResponse:
        agent_code = payload.agent_code.strip()
        agent_name = payload.agent_name.strip()
        if not agent_code:
            raise ValidationError("agent_code is required")
        if not agent_name:
            raise ValidationError("agent_name is required")
        if await self._repository.get_by_code(agent_code):
            raise ConflictError("agent_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        token = secrets.token_urlsafe(AGENT_TOKEN_BYTES)
        row = await self._repository.create(
            id=new_id(),
            agent_code=agent_code,
            agent_name=agent_name,
            host_id=int(payload.host_id) if payload.host_id else None,
            token_hash=_hash_token(token),
            version=payload.version,
            status="UNKNOWN",
            enabled=True,
            registered_at=now,
            metadata_payload=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_AGENT_REGISTER",
            actor=actor,
            resource_type="ops_agent",
            resource_id=int(row.id),
            after_data={
                "agent_code": agent_code,
                "agent_name": agent_name,
                "host_id": str(int(row.host_id)) if row.host_id else None,
            },
        )
        await write_operation_log(
            self._session,
            operation="OPS_AGENT_REGISTER",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_agent",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return AgentRegisterResponse(
            **self._to_response(row).model_dump(),
            token=token,
        )

    async def set_agent_enabled(
        self, actor: Principal, agent_id: int, *, enabled: bool
    ) -> AgentResponse:
        row = await self._repository.get(agent_id)
        if row is None:
            raise NotFoundError("agent not found")
        before = {"enabled": bool(row.enabled), "status": str(row.status)}
        changes: dict[str, object] = {
            "enabled": enabled,
            "status": AGENT_STATUS_ONLINE if enabled else AGENT_STATUS_OFFLINE,
        }
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        action = "OPS_AGENT_ENABLE" if enabled else "OPS_AGENT_DISABLE"
        await self._audit.record(
            action=action,
            actor=actor,
            resource_type="ops_agent",
            resource_id=int(row.id),
            before_data=before,
            after_data={"enabled": enabled, "status": changes["status"]},
        )
        await write_operation_log(
            self._session,
            operation=action,
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_agent",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def record_heartbeat(
        self,
        payload: AgentHeartbeatRequest,
        *,
        header_agent_code: str | None = None,
        header_token: str | None = None,
        client_ip: str | None = None,
    ) -> AgentHeartbeatAcceptedResponse:
        """Accept, verify and store one heartbeat reported by an agent.

        Every rejection is a ``401`` with the same message: distinguishing an
        unknown code from a wrong token would turn this endpoint into an
        oracle, and echoing the token would leak it.
        """
        agent_code = payload.agent_code or header_agent_code
        token = payload.token or header_token
        if not agent_code or not token:
            raise AuthenticationError("agent credentials are required")
        row = await self._repository.get_by_code(agent_code.strip())
        if row is None or not row.enabled:
            raise AuthenticationError("agent credentials are invalid")
        if not hmac.compare_digest(_hash_token(token), str(row.token_hash)):
            raise AuthenticationError("agent credentials are invalid")

        now = datetime.datetime.now(datetime.UTC)
        collected_at = payload.collected_at or now
        await self._repository.add_heartbeat(
            id=new_id(),
            agent_id=int(row.id),
            cpu_usage=payload.cpu_usage,
            memory_usage=payload.memory_usage,
            disk_usage=payload.disk_usage,
            load1=payload.load1,
            load5=payload.load5,
            load15=payload.load15,
            net_rx_bytes=payload.net_rx_bytes,
            net_tx_bytes=payload.net_tx_bytes,
            uptime_seconds=payload.uptime_seconds,
            collected_at=collected_at,
        )
        await self._repository.update(
            row,
            last_heartbeat_at=collected_at,
            status=AGENT_STATUS_ONLINE,
            ip_address=payload.ip_address or client_ip or row.ip_address,
            version=payload.version or row.version,
            updated_at=now,
        )

        host = await self._repository.get_host(int(row.host_id)) if row.host_id else None
        if host is not None:
            host.last_seen_at = collected_at
            host.status = HOST_STATUS_ONLINE
            host.updated_at = now
            await self._session.flush()

        metric_keys = await self._project_metrics(
            agent=row, payload=payload, host_environment=_environment_of(host), at=collected_at
        )
        await write_operation_log(
            self._session,
            operation="OPS_AGENT_HEARTBEAT",
            result=RESULT_SUCCESS,
            resource_type="ops_agent",
            resource_id=int(row.id),
            metadata={
                "agent_code": str(row.agent_code),
                "collected_at": collected_at.isoformat(),
                "metric_keys": metric_keys,
            },
        )
        await self._session.commit()
        return AgentHeartbeatAcceptedResponse(
            agent_id=str(int(row.id)),
            agent_code=str(row.agent_code),
            status=str(row.status),
            collected_at=collected_at,
            metric_keys=metric_keys,
        )

    async def list_heartbeats(
        self, agent_id: int, *, hours: int, page: PageParams
    ) -> Page[AgentHeartbeatResponse]:
        row = await self._repository.get(agent_id)
        if row is None:
            raise NotFoundError("agent not found")
        since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
        rows, total = await self._repository.list_heartbeats(
            agent_id=agent_id, since=since, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_heartbeat_response(item) for item in rows],
            total=total,
            params=page,
        )

    async def _project_metrics(
        self,
        *,
        agent: OpsAgent,
        payload: AgentHeartbeatRequest,
        host_environment: str,
        at: datetime.datetime,
    ) -> list[str]:
        """Write the usage metrics of a heartbeat into ``ops_metric_sample``.

        Only the metrics the agent actually reported are written: an absent
        value is unknown, not zero, and a fabricated zero would pollute every
        later aggregation.
        """
        labels = {"agent_code": str(agent.agent_code)}
        samples: list[dict[str, object]] = []
        metric_keys: list[str] = []
        reported = (
            (METRIC_KEY_HOST_CPU_USAGE, payload.cpu_usage),
            (METRIC_KEY_HOST_MEMORY_USAGE, payload.memory_usage),
            (METRIC_KEY_HOST_DISK_USAGE, payload.disk_usage),
        )
        for metric_key, value in reported:
            if value is None:
                continue
            samples.append(
                {
                    "id": new_id(),
                    "metric_key": metric_key,
                    "host_id": int(agent.host_id) if agent.host_id else None,
                    "environment": host_environment,
                    "value": float(value),
                    "labels": labels,
                    "collected_at": at,
                }
            )
            metric_keys.append(metric_key)
        await self._repository.add_metric_samples(samples)
        return metric_keys

    def _to_response(self, row: OpsAgent) -> AgentResponse:
        return AgentResponse(
            id=str(int(row.id)),
            agent_code=str(row.agent_code),
            agent_name=str(row.agent_name),
            host_id=str(int(row.host_id)) if row.host_id else None,
            version=row.version,
            ip_address=row.ip_address,
            status=str(row.status),
            enabled=bool(row.enabled),
            last_heartbeat_at=row.last_heartbeat_at,
            registered_at=row.registered_at,
            metadata=row.metadata_payload,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_heartbeat_response(self, row: OpsAgentHeartbeat) -> AgentHeartbeatResponse:
        return AgentHeartbeatResponse(
            id=str(int(row.id)),
            agent_id=str(int(row.agent_id)),
            cpu_usage=row.cpu_usage,
            memory_usage=row.memory_usage,
            disk_usage=row.disk_usage,
            load1=row.load1,
            load5=row.load5,
            load15=row.load15,
            net_rx_bytes=row.net_rx_bytes,
            net_tx_bytes=row.net_tx_bytes,
            uptime_seconds=row.uptime_seconds,
            collected_at=row.collected_at,
            created_at=row.created_at,
        )


def _hash_token(token: str) -> str:
    """Return the stored representation of a plain agent token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _environment_of(host: OpsHost | None) -> str:
    """Return the environment a sample belongs to.

    A heartbeat is reported by an agent, but a sample is a fact about the host
    the agent runs on, so the host environment wins and the default is only a
    fallback for an agent that is not bound to a host yet.
    """
    if host is not None and host.environment:
        return str(host.environment)
    return DEFAULT_ENVIRONMENT
