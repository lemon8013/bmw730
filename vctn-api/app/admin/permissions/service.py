"""app.admin.permissions — business logic."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.permissions.model import SysPermission, SysPermissionField
from app.admin.permissions.repository import PermissionRepository
from app.admin.permissions.schema import (
    CreateResourceRequest,
    FieldPermissionOutput,
    PermissionResourceResponse,
    PermissionTreeNode,
    UpdateResourceRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

ACTIVE_STATUS: str = "ACTIVE"


class PermissionService:
    """Permission resource management, including field level policies."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = PermissionRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def tree(self) -> list[PermissionTreeNode]:
        """Return the permission tree."""
        rows = await self._repository.list_all()
        nodes = {
            int(row.id): PermissionTreeNode(
                id=str(int(row.id)),
                permission_code=str(row.permission_code),
                permission_name=str(row.permission_name),
                permission_type=str(row.permission_type),
                resource_type=str(row.resource_type),
                resource_code=str(row.resource_code),
                status=str(row.status),
                sort_order=int(row.sort_order or 0),
            )
            for row in rows
        }
        roots: list[PermissionTreeNode] = []
        for row in rows:
            node = nodes[int(row.id)]
            parent_id = row.parent_id
            if parent_id is not None and int(parent_id) in nodes:
                nodes[int(parent_id)].children.append(node)
            else:
                roots.append(node)
        return roots

    async def list_resources(self, *, page: PageParams) -> Page[PermissionResourceResponse]:
        """Return one page of resources, each with its field policies.

        Two queries in total, whatever the page size: one for the rows of the
        page and one for their field policies. Paginating in the database keeps
        the cost proportional to the page rather than to the table.
        """
        total = await self._repository.count_all()
        rows = await self._repository.list_page(offset=page.offset, limit=page.limit)
        field_map = await self._repository.fields_of_many([int(row.id) for row in rows])
        items = [
            self._build_response(row, field_map.get(int(row.id), [])) for row in rows
        ]
        return Page.build(items=items, total=total, params=page)

    async def get_resource(self, permission_id: int) -> PermissionResourceResponse:
        row = await self._repository.get(permission_id)
        if row is None:
            raise NotFoundError("permission resource not found")
        return await self._to_response(row)

    async def create_resource(
        self, actor: Principal, payload: CreateResourceRequest
    ) -> PermissionResourceResponse:
        if await self._repository.exists_code(payload.permission_code):
            raise ConflictError("permission code is already taken")
        parent_id = int(payload.parent_id) if payload.parent_id else None
        if parent_id is not None and await self._repository.get(parent_id) is None:
            raise NotFoundError("parent permission resource not found")

        row = SysPermission(
            id=new_id(),
            permission_code=payload.permission_code,
            permission_name=payload.permission_name,
            permission_type=payload.permission_type,
            resource_type=payload.resource_type,
            resource_code=payload.resource_code,
            parent_id=parent_id,
            status=ACTIVE_STATUS,
            sort_order=payload.sort_order,
            description=payload.description,
        )
        self._repository.add(row)
        await self._session.flush()
        await self._repository.replace_fields(
            int(row.id),
            [(item.field_code, item.field_mode) for item in payload.field_permissions],
        )
        await self._audit.record(
            self._session,
            action="PERMISSION_RESOURCE_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_permission",
            resource_id=int(row.id),
            after_data={
                "permission_code": row.permission_code,
                "resource_code": row.resource_code,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="PERMISSION_RESOURCE_CREATE",
            result=RESULT_SUCCESS,
            operator_id=actor.subject_id,
            resource_type="sys_permission",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row)

    async def update_resource(
        self, actor: Principal, permission_id: int, payload: UpdateResourceRequest
    ) -> PermissionResourceResponse:
        row = await self._repository.get(permission_id)
        if row is None:
            raise NotFoundError("permission resource not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        before = {
            "permission_name": row.permission_name,
            "resource_type": row.resource_type,
            "resource_code": row.resource_code,
            "status": row.status,
            "sort_order": row.sort_order,
        }
        for field_name, value in changes.items():
            if field_name == "field_permissions":
                await self._repository.replace_fields(
                    permission_id, [(item["field_code"], item["field_mode"]) for item in value]
                )
                continue
            if field_name == "parent_id":
                target = int(value)
                if target == permission_id:
                    raise BusinessRuleError("a permission cannot be its own parent")
                if await self._repository.get(target) is None:
                    raise NotFoundError("parent permission resource not found")
                setattr(row, field_name, target)
                continue
            setattr(row, field_name, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="PERMISSION_RESOURCE_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_permission",
            resource_id=permission_id,
            before_data=before,
            after_data={
                "permission_name": row.permission_name,
                "resource_type": row.resource_type,
                "resource_code": row.resource_code,
                "status": row.status,
                "sort_order": row.sort_order,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(row)

    async def delete_resource(self, actor: Principal, permission_id: int) -> None:
        row = await self._repository.get(permission_id)
        if row is None:
            raise NotFoundError("permission resource not found")
        if await self._repository.has_children(permission_id):
            raise BusinessRuleError("a permission with children cannot be deleted")

        now = datetime.datetime.now(datetime.UTC)
        row.deleted_at = now
        row.status = "DISABLED"
        await self._repository.replace_fields(permission_id, [])
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="PERMISSION_RESOURCE_DELETE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_permission",
            resource_id=permission_id,
            after_data={"deleted_at": now.isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()

    async def _to_response(self, row: SysPermission) -> PermissionResourceResponse:
        fields = await self._repository.fields_of(int(row.id))
        return self._build_response(row, fields)

    def _build_response(
        self, row: SysPermission, fields: Sequence[SysPermissionField]
    ) -> PermissionResourceResponse:
        """Render one resource; the caller supplies its already loaded fields."""
        return PermissionResourceResponse(
            id=str(int(row.id)),
            permission_code=str(row.permission_code),
            permission_name=str(row.permission_name),
            permission_type=str(row.permission_type),
            resource_type=str(row.resource_type),
            resource_code=str(row.resource_code),
            parent_id=None if row.parent_id is None else str(int(row.parent_id)),
            status=str(row.status),
            sort_order=int(row.sort_order or 0),
            description=row.description,
            field_permissions=[
                FieldPermissionOutput(
                    id=str(int(item.id)),
                    field_code=str(item.field_code),
                    field_mode=str(item.field_mode),
                )
                for item in fields
            ],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
