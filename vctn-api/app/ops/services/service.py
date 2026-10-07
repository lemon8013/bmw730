"""app.ops.services — 业务逻辑。

Service 是事务边界：每个写操作落审计、落操作日志，最后统一 commit。
服务状态与依赖类型的取值域在这里收敛，Repository 只按传入值写库。
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.services.model import OpsService, OpsServiceDependency
from app.ops.services.repository import ServiceRepository
from app.ops.services.schema import (
    ServiceCreateRequest,
    ServiceDependencyCreateRequest,
    ServiceDependencyResponse,
    ServiceResponse,
    ServiceUpdateRequest,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

SERVICE_STATUSES: frozenset[str] = frozenset(
    {"UP", "DOWN", "DEGRADED", "UNKNOWN", "MAINTENANCE"}
)
DEPENDENCY_TYPES: frozenset[str] = frozenset({"CALLS", "USES", "RUNS_ON"})


class ServiceService:
    """服务注册与依赖拓扑管理。"""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ServiceRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_services(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        environment: str | None = None,
        service_type: str | None = None,
        host_id: int | None = None,
        page: PageParams,
    ) -> Page[ServiceResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            status=status,
            environment=environment,
            service_type=service_type,
            host_id=host_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_service(self, service_id: int) -> ServiceResponse:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        return self._to_response(row)

    async def create_service(
        self, actor: Principal, payload: ServiceCreateRequest
    ) -> ServiceResponse:
        service_code = payload.service_code.strip()
        if not service_code:
            raise ValidationError("service_code is required")
        if not payload.service_name.strip():
            raise ValidationError("service_name is required")
        if await self._repository.get_by_code(service_code):
            raise ConflictError("service_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            service_code=service_code,
            service_name=payload.service_name,
            service_type=payload.service_type,
            environment=payload.environment,
            host_id=int(payload.host_id) if payload.host_id else None,
            status="UNKNOWN",
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_SERVICE_CREATE",
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
            after_data={"service_code": service_code, "environment": payload.environment},
        )
        await write_operation_log(
            self._session,
            operation="OPS_SERVICE_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def update_service(
        self, actor: Principal, service_id: int, payload: ServiceUpdateRequest
    ) -> ServiceResponse:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "status" in changes and changes["status"] not in SERVICE_STATUSES:
            raise ValidationError(f"status must be one of {sorted(SERVICE_STATUSES)}")
        if "host_id" in changes:
            changes["host_id"] = int(changes["host_id"]) if changes["host_id"] else None
        before = {"status": row.status, "environment": row.environment}
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_SERVICE_UPDATE",
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_SERVICE_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_service(self, actor: Principal, service_id: int) -> None:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        await self._repository.soft_delete(row)
        await self._audit.record(
            action="OPS_SERVICE_DELETE",
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat() if row.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_SERVICE_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_service",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def list_dependencies(
        self, service_id: int, *, page: PageParams
    ) -> Page[ServiceDependencyResponse]:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        rows, total = await self._repository.list_dependencies(
            service_id=service_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_dependency_response(item) for item in rows],
            total=total,
            params=page,
        )

    async def add_dependency(
        self, actor: Principal, service_id: int, payload: ServiceDependencyCreateRequest
    ) -> ServiceDependencyResponse:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        depends_on_service_id = int(payload.depends_on_service_id)
        if depends_on_service_id == service_id:
            # 自环边会让拓扑遍历与告警收敛同时死循环，所以在入口就拒绝。
            raise ValidationError("a service cannot depend on itself")
        if payload.dependency_type not in DEPENDENCY_TYPES:
            raise ValidationError(f"dependency_type must be one of {sorted(DEPENDENCY_TYPES)}")
        depends_on = await self._repository.get(depends_on_service_id)
        if depends_on is None:
            raise NotFoundError("depends_on service not found")
        if await self._repository.find_dependency(
            service_id=service_id, depends_on_service_id=depends_on_service_id
        ):
            raise ConflictError("dependency already exists")
        now = datetime.datetime.now(datetime.UTC)
        edge = await self._repository.create_dependency(
            id=new_id(),
            service_id=service_id,
            depends_on_service_id=depends_on_service_id,
            dependency_type=payload.dependency_type,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_SERVICE_DEPENDENCY_CREATE",
            actor=actor,
            resource_type="ops_service_dependency",
            resource_id=int(edge.id),
            after_data={
                "service_id": str(service_id),
                "depends_on_service_id": str(depends_on_service_id),
                "dependency_type": payload.dependency_type,
            },
        )
        await write_operation_log(
            self._session,
            operation="OPS_SERVICE_DEPENDENCY_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_service_dependency",
            resource_id=int(edge.id),
        )
        await self._session.commit()
        return self._to_dependency_response(edge)

    async def remove_dependency(
        self, actor: Principal, service_id: int, dependency_id: int
    ) -> None:
        row = await self._repository.get(service_id)
        if row is None:
            raise NotFoundError("service not found")
        edge = await self._repository.get_dependency(
            service_id=service_id, dependency_id=dependency_id
        )
        if edge is None:
            raise NotFoundError("dependency not found")
        await self._repository.soft_delete_dependency(edge)
        await self._audit.record(
            action="OPS_SERVICE_DEPENDENCY_DELETE",
            actor=actor,
            resource_type="ops_service_dependency",
            resource_id=int(edge.id),
            after_data={"deleted_at": edge.deleted_at.isoformat() if edge.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_SERVICE_DEPENDENCY_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_service_dependency",
            resource_id=int(edge.id),
        )
        await self._session.commit()

    def _to_response(self, row: OpsService) -> ServiceResponse:
        return ServiceResponse(
            id=str(int(row.id)),
            service_code=str(row.service_code),
            service_name=str(row.service_name),
            service_type=str(row.service_type),
            environment=str(row.environment),
            host_id=str(int(row.host_id)) if row.host_id else None,
            status=str(row.status),
            last_check_at=row.last_check_at,
            availability_rate=row.availability_rate,
            error_rate=row.error_rate,
            avg_latency_ms=row.avg_latency_ms,
            tags=row.tags,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_dependency_response(self, row: OpsServiceDependency) -> ServiceDependencyResponse:
        return ServiceDependencyResponse(
            id=str(int(row.id)),
            service_id=str(int(row.service_id)),
            depends_on_service_id=str(int(row.depends_on_service_id)),
            dependency_type=str(row.dependency_type),
            created_at=row.created_at,
        )
