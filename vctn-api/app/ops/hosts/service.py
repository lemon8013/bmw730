"""app.ops.hosts — business logic.

The service owns the transaction: every mutation commits at the end and writes
an audit record plus an operation log. Threshold and status semantics are never
decided in the repository.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.hosts.model import OpsHost
from app.ops.hosts.repository import HostRepository
from app.ops.hosts.schema import (
    EnvironmentResponse,
    HostCreateRequest,
    HostGroupResponse,
    HostResponse,
    HostUpdateRequest,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

HOST_STATUSES: frozenset[str] = frozenset(
    {"ONLINE", "OFFLINE", "UNKNOWN", "MAINTENANCE"}
)


class HostService:
    """Host registry management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = HostRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_hosts(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        environment: str | None = None,
        host_group_id: int | None = None,
        page: PageParams,
    ) -> Page[HostResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            status=status,
            environment=environment,
            host_group_id=host_group_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_host(self, host_id: int) -> HostResponse:
        row = await self._repository.get(host_id)
        if row is None:
            raise NotFoundError("host not found")
        return self._to_response(row)

    async def create_host(self, actor: Principal, payload: HostCreateRequest) -> HostResponse:
        hostname = payload.hostname.strip()
        if not hostname:
            raise ValidationError("hostname is required")
        if await self._repository.get_by_hostname(hostname):
            raise ConflictError("hostname is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            hostname=hostname,
            display_name=payload.display_name,
            ip_address=payload.ip_address,
            os_type=payload.os_type,
            os_version=payload.os_version,
            cpu_cores=payload.cpu_cores,
            memory_total_mb=payload.memory_total_mb,
            disk_total_gb=payload.disk_total_gb,
            environment=payload.environment,
            host_group_id=int(payload.host_group_id) if payload.host_group_id else None,
            status="UNKNOWN",
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_HOST_CREATE",
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
            after_data={"hostname": hostname, "environment": payload.environment},
        )
        await write_operation_log(
            self._session,
            operation="OPS_HOST_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def update_host(
        self, actor: Principal, host_id: int, payload: HostUpdateRequest
    ) -> HostResponse:
        row = await self._repository.get(host_id)
        if row is None:
            raise NotFoundError("host not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "status" in changes and changes["status"] not in HOST_STATUSES:
            raise ValidationError(f"status must be one of {sorted(HOST_STATUSES)}")
        if "host_group_id" in changes:
            changes["host_group_id"] = (
                int(changes["host_group_id"]) if changes["host_group_id"] else None
            )
        before = {"status": row.status, "environment": row.environment}
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_HOST_UPDATE",
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_HOST_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_host(self, actor: Principal, host_id: int) -> None:
        row = await self._repository.get(host_id)
        if row is None:
            raise NotFoundError("host not found")
        await self._repository.soft_delete(row)
        await self._audit.record(
            action="OPS_HOST_DELETE",
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat() if row.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_HOST_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_host",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def list_host_groups(self) -> list[HostGroupResponse]:
        rows = await self._repository.list_groups()
        return [
            HostGroupResponse(
                id=str(int(row.id)),
                group_code=str(row.group_code),
                group_name=str(row.group_name),
                description=row.description,
                sort_order=int(row.sort_order or 0),
            )
            for row in rows
        ]

    async def list_environments(self) -> list[EnvironmentResponse]:
        rows = await self._repository.list_environments()
        return [
            EnvironmentResponse(
                id=str(int(row.id)),
                env_code=str(row.env_code),
                env_name=str(row.env_name),
                description=row.description,
                sort_order=int(row.sort_order or 0),
            )
            for row in rows
        ]

    def _to_response(self, row: OpsHost) -> HostResponse:
        return HostResponse(
            id=str(int(row.id)),
            hostname=str(row.hostname),
            display_name=row.display_name,
            ip_address=row.ip_address,
            os_type=row.os_type,
            os_version=row.os_version,
            cpu_cores=row.cpu_cores,
            memory_total_mb=row.memory_total_mb,
            disk_total_gb=row.disk_total_gb,
            environment=str(row.environment),
            host_group_id=str(int(row.host_group_id)) if row.host_group_id else None,
            agent_id=str(int(row.agent_id)) if row.agent_id else None,
            status=str(row.status),
            last_seen_at=row.last_seen_at,
            tags=row.tags,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
