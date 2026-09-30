"""app.admin.roles — business logic."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.departments.repository import DepartmentRepository
from app.admin.roles.model import SysRole
from app.admin.roles.repository import RoleRepository
from app.admin.roles.schema import (
    AssignParentsRequest,
    AssignPermissionsRequest,
    CreateRoleRequest,
    ParentRoleBrief,
    PermissionBrief,
    RoleResponse,
    UpdateRoleRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.authorization.service import (
    SCOPE_ALL,
    SCOPE_CUSTOM,
    SCOPE_DEPARTMENT,
    SCOPE_DEPARTMENT_CHILDREN,
    SCOPE_SELF,
    AuthorizationService,
)
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

ACTIVE_STATUS: str = "ACTIVE"
VALID_DATA_SCOPES = (
    SCOPE_ALL,
    SCOPE_DEPARTMENT,
    SCOPE_DEPARTMENT_CHILDREN,
    SCOPE_SELF,
    SCOPE_CUSTOM,
)


class RoleService:
    """Role, role permission and role inheritance management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = RoleRepository(session)
        self._departments = DepartmentRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._authorization = AuthorizationService(self._settings)

    async def list_roles(self, actor: Principal, *, page: PageParams) -> Page[RoleResponse]:
        rows = await self._repository.list_all()
        counts = await self._repository.user_counts()
        items = [await self._to_response(row, counts) for row in rows]
        total = len(items)
        window = items[page.offset : page.offset + page.limit]
        return Page.build(items=window, total=total, params=page)

    async def get_role(self, actor: Principal, role_id: int) -> RoleResponse:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        return await self._to_response(row, await self._repository.user_counts())

    async def create_role(self, actor: Principal, payload: CreateRoleRequest) -> RoleResponse:
        if payload.data_scope not in VALID_DATA_SCOPES:
            raise BusinessRuleError(f"data_scope must be one of {list(VALID_DATA_SCOPES)}")
        if await self._repository.exists_code(payload.role_code):
            raise ConflictError("role code is already taken")
        if not actor.is_super_admin and payload.data_scope == SCOPE_ALL:
            await self._audit.record_failure(
                self._session,
                action="ROLE_CREATE",
                error_code="ROLE_ESCALATION",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_role",
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("only a super administrator may grant the ALL data scope")

        row = SysRole(
            id=new_id(),
            role_code=payload.role_code,
            role_name=payload.role_name,
            description=payload.description,
            status=ACTIVE_STATUS,
            data_scope=payload.data_scope,
        )
        self._repository.add(row)
        await self._session.flush()
        await self._replace_custom_scopes(
            int(row.id), payload.data_scope, payload.custom_department_ids
        )
        await self._audit.record(
            self._session,
            action="ROLE_CREATE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_role",
            resource_id=int(row.id),
            after_data={"role_code": row.role_code, "data_scope": row.data_scope},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="ROLE_CREATE",
            result=RESULT_SUCCESS,
            operator_id=actor.subject_id,
            resource_type="sys_role",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row, await self._repository.user_counts())

    async def update_role(
        self, actor: Principal, role_id: int, payload: UpdateRoleRequest
    ) -> RoleResponse:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        modes = await self._authorization.field_modes(self._session, actor, "ROLE_EDIT")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        self._authorization.assert_editable(changes, modes, resource="sys_role")

        before = {
            "role_name": row.role_name,
            "status": row.status,
            "data_scope": row.data_scope,
            "description": row.description,
        }
        data_scope = str(row.data_scope)
        custom_department_ids: list[str] | None = None
        for field_name, value in changes.items():
            if field_name == "custom_department_ids":
                custom_department_ids = [str(item) for item in value]
                continue
            if field_name == "data_scope":
                if value not in VALID_DATA_SCOPES:
                    raise BusinessRuleError(f"data_scope must be one of {list(VALID_DATA_SCOPES)}")
                if value == SCOPE_ALL and not actor.is_super_admin:
                    await self._audit.record_failure(
                        self._session,
                        action="ROLE_EDIT",
                        error_code="ROLE_ESCALATION",
                        operator_id=actor.subject_id,
                        operator_username=actor.username,
                        resource_type="sys_role",
                        resource_id=role_id,
                        ip=actor.ip,
                        user_agent=actor.user_agent,
                    )
                    await self._session.commit()
                    raise BusinessRuleError(
                        "only a super administrator may grant the ALL data scope"
                    )
                data_scope = str(value)
            setattr(row, field_name, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        if custom_department_ids is not None:
            await self._replace_custom_scopes(role_id, data_scope, custom_department_ids)

        await self._audit.record(
            self._session,
            action="ROLE_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_role",
            resource_id=role_id,
            before_data=before,
            after_data={
                "role_name": row.role_name,
                "status": row.status,
                "data_scope": row.data_scope,
                "description": row.description,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(row, await self._repository.user_counts())

    async def delete_role(self, actor: Principal, role_id: int) -> None:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        if await self._repository.has_members(role_id):
            raise BusinessRuleError("a role that is still assigned cannot be deleted")

        now = datetime.datetime.now(datetime.UTC)
        row.deleted_at = now
        row.status = "DISABLED"
        await self._repository.replace_permissions(role_id, [])
        await self._repository.replace_parents(role_id, [])
        await self._repository.replace_data_scopes(role_id, [])
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="ROLE_DELETE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_role",
            resource_id=role_id,
            after_data={"deleted_at": now.isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()

    async def role_permissions(self, actor: Principal, role_id: int) -> list[PermissionBrief]:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        rows = await self._repository.permissions_of(role_id)
        return [PermissionBrief.model_validate(item) for item in rows]

    async def assign_permissions(
        self, actor: Principal, role_id: int, payload: AssignPermissionsRequest
    ) -> list[PermissionBrief]:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        permission_ids = [int(value) for value in payload.permission_ids]
        found = await self._repository.find_permissions(permission_ids)
        if len(found) != len(set(permission_ids)):
            raise NotFoundError("one or more permissions do not exist")
        await self._assert_permissions_grantable(actor, permission_ids)

        before = [int(item.id) for item in await self._repository.permissions_of(role_id)]
        await self._repository.replace_permissions(role_id, permission_ids)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="ROLE_PERMISSION_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_role",
            resource_id=role_id,
            before_data={"permission_ids": before},
            after_data={"permission_ids": permission_ids},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return [
            PermissionBrief.model_validate(item)
            for item in await self._repository.permissions_of(role_id)
        ]

    async def role_parents(self, actor: Principal, role_id: int) -> list[ParentRoleBrief]:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        rows = await self._repository.parents_of(role_id)
        return [ParentRoleBrief.model_validate(item) for item in rows]

    async def assign_parents(
        self, actor: Principal, role_id: int, payload: AssignParentsRequest
    ) -> list[ParentRoleBrief]:
        row = await self._repository.get(role_id)
        if row is None:
            raise NotFoundError("role not found")
        parent_ids = [int(value) for value in payload.parent_role_ids]
        existing = {int(item.id) for item in await self._repository.list_all()}
        missing = sorted(set(parent_ids) - existing)
        if missing:
            raise NotFoundError("one or more parent roles do not exist")
        if await self._repository.would_cycle(role_id, parent_ids):
            await self._audit.record_failure(
                self._session,
                action="ROLE_INHERIT_EDIT",
                error_code="ROLE_CYCLE",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_role",
                resource_id=role_id,
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("the inheritance change would create a cycle")

        before = [int(item.id) for item in await self._repository.parents_of(role_id)]
        await self._repository.replace_parents(role_id, parent_ids)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="ROLE_INHERIT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_role",
            resource_id=role_id,
            before_data={"parent_role_ids": before},
            after_data={"parent_role_ids": parent_ids},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        rows = await self._repository.parents_of(role_id)
        return [ParentRoleBrief.model_validate(item) for item in rows]

    async def _assert_permissions_grantable(
        self, actor: Principal, permission_ids: list[int]
    ) -> None:
        """A non super administrator may only grant permissions it holds."""
        if actor.is_super_admin or not permission_ids:
            return
        held = await self._authorization.permission_codes(self._session, actor)
        granted = await self._repository.find_permissions(permission_ids)
        escalation = sorted(
            {str(item.permission_code) for item in granted if str(item.permission_code) not in held}
        )
        if escalation:
            await self._audit.record_failure(
                self._session,
                action="ROLE_PERMISSION_EDIT",
                error_code="PERMISSION_ESCALATION",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_permission",
                resource_id=",".join(escalation),
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("a permission can only be granted when the operator holds it")

    async def _replace_custom_scopes(
        self, role_id: int, data_scope: str, department_ids: list[str]
    ) -> None:
        if data_scope != SCOPE_CUSTOM:
            await self._repository.replace_data_scopes(role_id, [])
            return
        entries: list[tuple[str, int | None]] = []
        for raw in department_ids:
            department_id = int(raw)
            if await self._departments.get(department_id) is None:
                raise NotFoundError("department not found")
            entries.append((SCOPE_DEPARTMENT, department_id))
        if not entries:
            raise BusinessRuleError("a CUSTOM data scope needs at least one department")
        await self._repository.replace_data_scopes(role_id, entries)

    async def _to_response(self, row: SysRole, counts: dict[int, int]) -> RoleResponse:
        custom: list[str] = []
        if str(row.data_scope) == SCOPE_CUSTOM:
            custom = [
                str(int(item.department_id))
                for item in await self._repository.data_scopes_of(int(row.id))
                if item.department_id is not None
            ]
        return RoleResponse(
            id=str(int(row.id)),
            role_code=str(row.role_code),
            role_name=str(row.role_name),
            description=row.description,
            status=str(row.status),
            data_scope=str(row.data_scope),
            custom_department_ids=custom,
            user_count=counts.get(int(row.id), 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def role_summary(row: SysRole) -> dict[str, Any]:
    """Return a compact role summary for embedding in other payloads."""
    return {
        "id": str(int(row.id)),
        "role_code": str(row.role_code),
        "role_name": str(row.role_name),
        "data_scope": str(row.data_scope),
    }
