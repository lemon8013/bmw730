"""app.admin.departments — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.departments.model import SysDepartment
from app.admin.departments.repository import DepartmentRepository
from app.admin.departments.schema import (
    CreateDepartmentRequest,
    DepartmentResponse,
    DepartmentTreeNode,
    UpdateDepartmentRequest,
)
from app.admin.users.repository import AdminUserRepository
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.authorization.service import AuthorizationService
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

ACTIVE_STATUS: str = "ACTIVE"


class DepartmentService:
    """Department management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = DepartmentRepository(session)
        self._users = AdminUserRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._authorization = AuthorizationService(self._settings)

    async def list_departments(
        self, actor: Principal, *, page: PageParams
    ) -> Page[DepartmentResponse]:
        scope_ids = await self._authorization.manageable_department_ids(self._session, actor)
        rows = await self._repository.list_visible(None if scope_ids is None else list(scope_ids))
        counts = await self._repository.user_counts()
        items = [await self._to_response(row, counts) for row in rows]
        total = len(items)
        window = items[page.offset : page.offset + page.limit]
        return Page.build(items=window, total=total, params=page)

    async def tree(self, actor: Principal) -> list[DepartmentTreeNode]:
        """Return the department tree limited by the caller's data scope."""
        scope_ids = await self._authorization.manageable_department_ids(self._session, actor)
        rows = await self._repository.list_visible(None if scope_ids is None else list(scope_ids))
        counts = await self._repository.user_counts()
        nodes = {
            int(row.id): DepartmentTreeNode(
                id=str(int(row.id)),
                parent_id=None if row.parent_id is None else str(int(row.parent_id)),
                department_code=str(row.department_code),
                department_name=str(row.department_name),
                status=str(row.status),
                sort_order=int(row.sort_order or 0),
                user_count=counts.get(int(row.id), 0),
            )
            for row in rows
        }
        roots: list[DepartmentTreeNode] = []
        for row in rows:
            node = nodes[int(row.id)]
            parent_id = row.parent_id
            if parent_id is not None and int(parent_id) in nodes:
                nodes[int(parent_id)].children.append(node)
            else:
                roots.append(node)
        return roots

    async def get_department(self, actor: Principal, department_id: int) -> DepartmentResponse:
        row = await self._repository.get(department_id)
        if row is None:
            raise NotFoundError("department not found")
        await self._authorization.assert_department_manageable(
            self._session, actor, department_id=department_id, action="DEPARTMENT_VIEW"
        )
        counts = await self._repository.user_counts()
        return await self._to_response(row, counts)

    async def children(self, actor: Principal, department_id: int) -> list[DepartmentResponse]:
        await self._authorization.assert_department_manageable(
            self._session, actor, department_id=department_id, action="DEPARTMENT_VIEW"
        )
        rows = await self._repository.children(department_id)
        counts = await self._repository.user_counts()
        return [await self._to_response(row, counts) for row in rows]

    async def users_of(self, actor: Principal, department_id: int) -> list[dict[str, object]]:
        await self._authorization.assert_department_manageable(
            self._session, actor, department_id=department_id, action="DEPARTMENT_VIEW"
        )
        rows = await self._repository.users_of(department_id)
        return [
            {
                "id": str(int(row.id)),
                "username": row.username,
                "display_name": row.display_name,
                "status": row.status,
                "department_id": str(department_id),
            }
            for row in rows
        ]

    async def create_department(
        self, actor: Principal, payload: CreateDepartmentRequest
    ) -> DepartmentResponse:
        parent_id = int(payload.parent_id) if payload.parent_id else None
        if parent_id is not None:
            parent = await self._repository.get(parent_id)
            if parent is None:
                raise NotFoundError("parent department not found")
            await self._authorization.assert_department_manageable(
                self._session, actor, department_id=parent_id, action="DEPARTMENT_CREATE"
            )
        if await self._repository.exists_code(payload.department_code):
            raise ConflictError("department code is already taken")

        row = SysDepartment(
            id=new_id(),
            parent_id=parent_id,
            department_code=payload.department_code,
            department_name=payload.department_name,
            status=ACTIVE_STATUS,
            sort_order=payload.sort_order,
            description=payload.description,
        )
        self._repository.add(row)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DEPARTMENT_CREATE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_department",
            resource_id=int(row.id),
            after_data={
                "department_code": row.department_code,
                "parent_id": parent_id,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="DEPARTMENT_CREATE",
            result=RESULT_SUCCESS,
            operator_id=actor.subject_id,
            resource_type="sys_department",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row, await self._repository.user_counts())

    async def update_department(
        self, actor: Principal, department_id: int, payload: UpdateDepartmentRequest
    ) -> DepartmentResponse:
        row = await self._repository.get(department_id)
        if row is None:
            raise NotFoundError("department not found")
        await self._authorization.assert_department_manageable(
            self._session, actor, department_id=department_id, action="DEPARTMENT_EDIT"
        )
        modes = await self._authorization.field_modes(self._session, actor, "DEPARTMENT_EDIT")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        self._authorization.assert_editable(changes, modes, resource="sys_department")

        before = {
            "department_name": row.department_name,
            "parent_id": row.parent_id,
            "sort_order": row.sort_order,
            "status": row.status,
        }
        for field_name, value in changes.items():
            if field_name == "parent_id":
                target = int(value)
                if target == department_id:
                    raise BusinessRuleError("a department cannot be its own parent")
                if await self._would_cycle(department_id, target):
                    raise BusinessRuleError("the parent change would create a cycle")
                parent = await self._repository.get(target)
                if parent is None:
                    raise NotFoundError("parent department not found")
                setattr(row, field_name, target)
                continue
            setattr(row, field_name, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DEPARTMENT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_department",
            resource_id=int(row.id),
            before_data=before,
            after_data={
                "department_name": row.department_name,
                "parent_id": row.parent_id,
                "sort_order": row.sort_order,
                "status": row.status,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(row, await self._repository.user_counts())

    async def delete_department(self, actor: Principal, department_id: int) -> None:
        row = await self._repository.get(department_id)
        if row is None:
            raise NotFoundError("department not found")
        await self._authorization.assert_department_manageable(
            self._session, actor, department_id=department_id, action="DEPARTMENT_DELETE"
        )
        children = await self._repository.children(department_id)
        if children:
            raise BusinessRuleError("a department with children cannot be deleted")
        user_count = await self._repository.count_users(department_id)
        if user_count:
            raise BusinessRuleError("a department that still has members cannot be deleted")

        await self._repository.soft_delete(row, now=datetime.datetime.now(datetime.UTC))
        await self._audit.record(
            self._session,
            action="DEPARTMENT_DELETE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_department",
            resource_id=int(row.id),
            before_data={"status": "ACTIVE"},
            after_data={"deleted_at": datetime.datetime.now(datetime.UTC).isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()

    async def _would_cycle(self, department_id: int, candidate_parent_id: int) -> bool:
        descendants = await self._repository.descendant_ids(department_id)
        return candidate_parent_id in descendants

    async def _to_response(self, row: SysDepartment, counts: dict[int, int]) -> DepartmentResponse:
        return DepartmentResponse(
            id=str(int(row.id)),
            parent_id=None if row.parent_id is None else str(int(row.parent_id)),
            department_code=str(row.department_code),
            department_name=str(row.department_name),
            status=str(row.status),
            sort_order=int(row.sort_order or 0),
            description=row.description,
            user_count=counts.get(int(row.id), 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
