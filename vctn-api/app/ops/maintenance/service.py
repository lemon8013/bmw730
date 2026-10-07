"""app.ops.maintenance — 业务逻辑。

Service 是事务边界：每个写操作落审计、落操作日志，最后统一 commit。时间区间
与作用域取值域这类策略在这里收敛，Repository 只按传入值写库。
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.maintenance.model import OpsMaintenanceWindow
from app.ops.maintenance.repository import MaintenanceRepository
from app.ops.maintenance.schema import (
    MaintenanceWindowCreateRequest,
    MaintenanceWindowResponse,
    MaintenanceWindowUpdateRequest,
)
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

SCOPE_TYPES: frozenset[str] = frozenset({"GLOBAL", "HOST", "SERVICE", "ENDPOINT"})

#: The scope whose windows suppress every alert, whatever the alert scope is.
SCOPE_TYPE_GLOBAL: str = "GLOBAL"


def is_window_suppressing(
    window: OpsMaintenanceWindow,
    at: datetime.datetime,
) -> bool:
    """Whether ``window`` suppresses alert notification at ``at``.

    Suppression is the whole point of ``suppress_alerts``, so all four guards
    have to hold: the window is not deleted, it is enabled, it was created to
    suppress, and ``at`` falls inside the closed interval. A window whose end
    equals ``at`` still suppresses, which is why the interval is closed: the
    operator booked the slot until that instant.
    """
    if getattr(window, "deleted_at", None) is not None:
        return False
    if not bool(getattr(window, "enabled", False)):
        return False
    if not bool(getattr(window, "suppress_alerts", False)):
        return False
    starts_at = getattr(window, "starts_at", None)
    ends_at = getattr(window, "ends_at", None)
    if starts_at is None or ends_at is None:
        return False
    return bool(starts_at <= at <= ends_at)


class MaintenanceService:
    """维护窗口管理。"""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = MaintenanceRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)

    async def list_windows(
        self,
        *,
        keyword: str | None = None,
        scope_type: str | None = None,
        scope_id: int | None = None,
        enabled: bool | None = None,
        active: bool | None = None,
        page: PageParams,
    ) -> Page[MaintenanceWindowResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            scope_type=scope_type,
            scope_id=scope_id,
            enabled=enabled,
            active_at=datetime.datetime.now(datetime.UTC) if active else None,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_window(self, window_id: int) -> MaintenanceWindowResponse:
        row = await self._repository.get(window_id)
        if row is None:
            raise NotFoundError("maintenance window not found")
        return self._to_response(row)

    async def suppresses_notifications(
        self,
        window: OpsMaintenanceWindow,
        *,
        at: datetime.datetime | None = None,
    ) -> bool:
        """Whether ``window`` suppresses alert notification at ``at``.

        Pure predicate over a loaded window: it never touches the database, so
        the notification dispatcher can reuse it on an object it already has.
        """
        moment = at if at is not None else datetime.datetime.now(datetime.UTC)
        return is_window_suppressing(window, moment)

    async def active_suppression(
        self,
        *,
        scope_type: str | None = None,
        scope_id: int | None = None,
        at: datetime.datetime | None = None,
    ) -> MaintenanceWindowResponse | None:
        """Return the window currently suppressing this scope, if any.

        This is the read the dispatcher performs before sending: a ``GLOBAL``
        window wins for every scope, a scoped window only for its own scope.
        """
        moment = at if at is not None else datetime.datetime.now(datetime.UTC)
        row = await self._repository.find_suppressing(
            at=moment, scope_type=scope_type, scope_id=scope_id
        )
        if row is None:
            return None
        return self._to_response(row)

    async def create_window(
        self, actor: Principal, payload: MaintenanceWindowCreateRequest
    ) -> MaintenanceWindowResponse:
        window_code = payload.window_code.strip()
        if not window_code:
            raise ValidationError("window_code is required")
        if not payload.title.strip():
            raise ValidationError("title is required")
        if payload.scope_type not in SCOPE_TYPES:
            raise ValidationError(f"scope_type must be one of {sorted(SCOPE_TYPES)}")
        # 结束时间必须先于开始时间之外：一个零长或倒挂的窗口会让告警抑制无限生效。
        if payload.ends_at <= payload.starts_at:
            raise ValidationError("ends_at must be greater than starts_at")
        if await self._repository.get_by_code(window_code):
            raise ConflictError("window_code is already registered")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            window_code=window_code,
            title=payload.title,
            reason=payload.reason,
            scope_type=payload.scope_type,
            scope_id=int(payload.scope_id) if payload.scope_id else None,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            suppress_alerts=payload.suppress_alerts,
            enabled=payload.enabled,
            created_by=actor.subject_id,
            created_by_username=actor.username,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            action="OPS_MAINTENANCE_CREATE",
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
            after_data={
                "window_code": window_code,
                "starts_at": payload.starts_at.isoformat(),
                "ends_at": payload.ends_at.isoformat(),
            },
        )
        await write_operation_log(
            self._session,
            operation="OPS_MAINTENANCE_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def update_window(
        self, actor: Principal, window_id: int, payload: MaintenanceWindowUpdateRequest
    ) -> MaintenanceWindowResponse:
        row = await self._repository.get(window_id)
        if row is None:
            raise NotFoundError("maintenance window not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise ValidationError("no field to update")
        if "scope_type" in changes and changes["scope_type"] not in SCOPE_TYPES:
            raise ValidationError(f"scope_type must be one of {sorted(SCOPE_TYPES)}")
        if "scope_id" in changes:
            changes["scope_id"] = int(changes["scope_id"]) if changes["scope_id"] else None
        # 只改一端时另一端取库里的值，保证组合后仍然是正区间。
        starts_at = changes.get("starts_at", row.starts_at)
        ends_at = changes.get("ends_at", row.ends_at)
        if ends_at <= starts_at:
            raise ValidationError("ends_at must be greater than starts_at")
        before = {
            "starts_at": row.starts_at.isoformat(),
            "ends_at": row.ends_at.isoformat(),
            "enabled": row.enabled,
        }
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        after = dict(changes)
        after["starts_at"] = starts_at.isoformat()
        after["ends_at"] = ends_at.isoformat()
        await self._audit.record(
            action="OPS_MAINTENANCE_UPDATE",
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
            before_data=before,
            after_data=after,
        )
        await write_operation_log(
            self._session,
            operation="OPS_MAINTENANCE_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_window(self, actor: Principal, window_id: int) -> None:
        row = await self._repository.get(window_id)
        if row is None:
            raise NotFoundError("maintenance window not found")
        await self._repository.soft_delete(row)
        await self._audit.record(
            action="OPS_MAINTENANCE_DELETE",
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat() if row.deleted_at else None},
        )
        await write_operation_log(
            self._session,
            operation="OPS_MAINTENANCE_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="ops_maintenance_window",
            resource_id=int(row.id),
        )
        await self._session.commit()

    def _to_response(self, row: OpsMaintenanceWindow) -> MaintenanceWindowResponse:
        return MaintenanceWindowResponse(
            id=str(int(row.id)),
            window_code=str(row.window_code),
            title=str(row.title),
            reason=row.reason,
            scope_type=str(row.scope_type),
            scope_id=str(int(row.scope_id)) if row.scope_id else None,
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            suppress_alerts=bool(row.suppress_alerts),
            enabled=bool(row.enabled),
            created_by=str(int(row.created_by)) if row.created_by else None,
            created_by_username=row.created_by_username,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
