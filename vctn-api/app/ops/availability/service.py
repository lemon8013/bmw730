"""app.ops.availability — 业务逻辑。

Service 是事务边界：每个写操作落审计、落操作日志，最后统一 commit。探测类型
取值域与"超时/间隔必须为正"这类策略在这里收敛，Repository 只按传入值写库。
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.availability.model import OpsAvailabilityCheck, OpsAvailabilityResult
from app.ops.availability.probe import run_probe
from app.ops.availability.repository import AvailabilityRepository
from app.ops.availability.schema import (
    AvailabilityCheckCreateRequest,
    AvailabilityCheckResponse,
    AvailabilityCheckUpdateRequest,
    AvailabilityResultResponse,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

CHECK_TYPES: frozenset[str] = frozenset({"HTTP", "TCP", "DNS", "SSL"})


class AvailabilityService:
    """可用性探测管理。"""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AvailabilityRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_checks(
        self,
        *,
        keyword: str | None = None,
        check_type: str | None = None,
        service_id: int | None = None,
        environment: str | None = None,
        enabled: bool | None = None,
        page: PageParams,
    ) -> Page[AvailabilityCheckResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            check_type=check_type,
            service_id=service_id,
            environment=environment,
            enabled=enabled,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_check(self, check_id: int) -> AvailabilityCheckResponse:
        row = await self._repository.get(check_id)
        if row is None:
            raise NotFoundError("availability check not found")
        return self._to_response(row)

    async def create_check(
        self, actor: Principal, payload: AvailabilityCheckCreateRequest
    ) -> AvailabilityCheckResponse:
        check_code = payload.check_code.strip()
        if not check_code:
            raise ValidationError("check_code is required")
        if not payload.name.strip():
            raise ValidationError("name is required")
        # 探测类型决定用哪个 provider 执行，写错就等于探测永远不会跑。
        if payload.check_type not in CHECK_TYPES:
            raise ValidationError(f"check_type must be one of {sorted(CHECK_TYPES)}")
        if not payload.target.strip():
            raise ValidationError("target is required")
        if payload.timeout_ms <= 0:
            raise ValidationError("timeout_ms must be greater than 0")
        if payload.interval_seconds <= 0:
            raise ValidationError("interval_seconds must be greater than 0")
        if await self._repository.get_by_code(check_code):
            raise ConflictError("check_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            check_code=check_code,
            name=payload.name,
            check_type=payload.check_type,
            target=payload.target,
            service_id=int(payload.service_id) if payload.service_id else None,
            environment=payload.environment,
            timeout_ms=payload.timeout_ms,
            interval_seconds=payload.interval_seconds,
            expected_status=payload.expected_status,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_AVAILABILITY_CREATE",
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
            after_data={"check_code": check_code, "check_type": payload.check_type},
        )
        await write_operation_log(
            self._session,
            operation="OPS_AVAILABILITY_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def update_check(
        self, actor: Principal, check_id: int, payload: AvailabilityCheckUpdateRequest
    ) -> AvailabilityCheckResponse:
        row = await self._repository.get(check_id)
        if row is None:
            raise NotFoundError("availability check not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "service_id" in changes:
            changes["service_id"] = (
                int(changes["service_id"]) if changes["service_id"] else None
            )
        if "timeout_ms" in changes and int(changes["timeout_ms"]) <= 0:
            raise ValidationError("timeout_ms must be greater than 0")
        if "interval_seconds" in changes and int(changes["interval_seconds"]) <= 0:
            raise ValidationError("interval_seconds must be greater than 0")
        before = {"target": row.target, "enabled": row.enabled}
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            action="OPS_AVAILABILITY_UPDATE",
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
            before_data=before,
            after_data=changes,
        )
        await write_operation_log(
            self._session,
            operation="OPS_AVAILABILITY_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_check(self, actor: Principal, check_id: int) -> None:
        row = await self._repository.get(check_id)
        if row is None:
            raise NotFoundError("availability check not found")
        await self._repository.soft_delete(row)
        await self._audit.record(
            action="OPS_AVAILABILITY_DELETE",
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat() if row.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_AVAILABILITY_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_availability_check",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def list_results(
        self,
        check_id: int,
        *,
        hours: int,
        success: bool | None = None,
        page: PageParams,
    ) -> Page[AvailabilityResultResponse]:
        row = await self._repository.get(check_id)
        if row is None:
            raise NotFoundError("availability check not found")
        since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
        rows, total = await self._repository.list_results(
            check_id=check_id,
            since=since,
            success=success,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_result_response(item) for item in rows],
            total=total,
            params=page,
        )

    async def run_due_checks(
        self, now: datetime.datetime | None = None
    ) -> dict[str, int]:
        """Execute every enabled check whose interval has elapsed.

        Called by the scheduler, so there is no actor to audit: a probe result
        is an observation, not an operator action. Every check is independent —
        one unreachable target must not stop the rest of the tick.
        """
        moment = now or datetime.datetime.now(datetime.UTC)
        outcome = {"due": 0, "succeeded": 0, "failed": 0}
        for check in await self._repository.list_enabled_checks():
            last_run = await self._repository.latest_result_at(int(check.id))
            if last_run is not None:
                next_due = last_run + datetime.timedelta(seconds=int(check.interval_seconds))
                if next_due > moment:
                    continue
            outcome["due"] += 1
            probe = await run_probe(check)
            await self._repository.create_result(
                id=new_id(),
                check_id=int(check.id),
                success=probe.success,
                latency_ms=probe.latency_ms,
                status_code=probe.status_code,
                error_message=probe.error_message,
                detail=probe.detail,
                checked_at=moment,
            )
            if probe.success:
                outcome["succeeded"] += 1
            else:
                outcome["failed"] += 1
        await self._session.commit()
        return outcome

    def _to_response(self, row: OpsAvailabilityCheck) -> AvailabilityCheckResponse:
        return AvailabilityCheckResponse(
            id=str(int(row.id)),
            check_code=str(row.check_code),
            name=str(row.name),
            check_type=str(row.check_type),
            target=str(row.target),
            service_id=str(int(row.service_id)) if row.service_id else None,
            environment=str(row.environment),
            timeout_ms=int(row.timeout_ms),
            interval_seconds=int(row.interval_seconds),
            expected_status=row.expected_status,
            enabled=bool(row.enabled),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_result_response(self, row: OpsAvailabilityResult) -> AvailabilityResultResponse:
        return AvailabilityResultResponse(
            id=str(int(row.id)),
            check_id=str(int(row.check_id)),
            success=bool(row.success),
            latency_ms=row.latency_ms,
            status_code=row.status_code,
            error_message=row.error_message,
            detail=row.detail,
            checked_at=row.checked_at,
        )
