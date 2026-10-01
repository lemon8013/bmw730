"""app.admin.tools — business logic.

Management entry point for the tool catalogue and its access policies. It reuses
the platform ``tools`` models and their repositories; it does not re-implement
tool runtime behaviour (resolution, quota enforcement, execution).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.tools.repository import AdminToolRepository
from app.admin.tools.schema import (
    AccessPolicyAdminResponse,
    AccessPolicyRequest,
    ToolCreateRequest,
    ToolStatusRequest,
    ToolUpdateRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.tools.catalog.schema import ToolResponse


class AdminToolService:
    """Administrative tool management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AdminToolRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_tools(
        self,
        *,
        status: str | None,
        category_id: int | None,
        keyword: str | None,
        page: PageParams,
    ) -> Page[ToolResponse]:
        rows, total = await self._repository.list_tools(
            status=status,
            category_id=category_id,
            keyword=keyword,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[ToolResponse.model_validate(row) for row in rows], total=total, params=page
        )

    async def get_tool(self, tool_id: int) -> ToolResponse:
        row = await self._repository.get_tool(tool_id)
        if row is None:
            raise NotFoundError("tool not found")
        return ToolResponse.model_validate(row)

    async def create_tool(
        self, *, actor_id: int, actor_username: str, payload: ToolCreateRequest
    ) -> ToolResponse:
        row = await self._repository.create_tool(
            code=payload.code,
            name=payload.name,
            slug=payload.slug,
            component_key=payload.component_key,
            execution_mode=payload.execution_mode,
            category_id=payload.category_id,
            icon=payload.icon,
            summary=payload.summary,
            description=payload.description,
            keywords=payload.keywords,
            tags=payload.tags,
            status=payload.status,
            sort_order=payload.sort_order,
        )
        await self._audit.record(
            self._session,
            action="TOOL_CREATE",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="tool",
            resource_id=row.id,
            after_data={"code": payload.code, "name": payload.name, "status": payload.status},
        )
        await write_operation_log(
            self._session,
            operation="TOOL_CREATE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="tool",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return ToolResponse.model_validate(row)

    async def update_tool(
        self, *, tool_id: int, actor_id: int, actor_username: str, payload: ToolUpdateRequest
    ) -> ToolResponse:
        row = await self._repository.get_tool(tool_id)
        if row is None:
            raise NotFoundError("tool not found")
        changes: dict[str, object] = {}
        for field in (
            "code",
            "name",
            "slug",
            "component_key",
            "execution_mode",
            "category_id",
            "icon",
            "summary",
            "description",
            "keywords",
            "tags",
            "status",
            "sort_order",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(row, field, value)
                changes[field] = value
        await self._repository.update_tool(row)
        if changes:
            await self._audit.record(
                self._session,
                action="TOOL_UPDATE",
                operator_id=int(actor_id),
                operator_username=actor_username,
                resource_type="tool",
                resource_id=row.id,
                after_data=changes,
            )
            await write_operation_log(
                self._session,
                operation="TOOL_UPDATE",
                result=RESULT_SUCCESS,
                operator_id=int(actor_id),
                resource_type="tool",
                resource_id=str(int(row.id)),
            )
        await self._session.commit()
        return ToolResponse.model_validate(row)

    async def set_status(
        self, *, tool_id: int, actor_id: int, actor_username: str, payload: ToolStatusRequest
    ) -> ToolResponse:
        row = await self._repository.get_tool(tool_id)
        if row is None:
            raise NotFoundError("tool not found")
        if not payload.status:
            raise ValidationError("status must not be empty")
        previous = str(row.status)
        row.status = payload.status
        await self._repository.update_tool(row)
        await self._audit.record(
            self._session,
            action="TOOL_STATUS_CHANGE",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="tool",
            resource_id=row.id,
            before_data={"status": previous},
            after_data={"status": payload.status},
        )
        await write_operation_log(
            self._session,
            operation="TOOL_STATUS_CHANGE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="tool",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return ToolResponse.model_validate(row)

    async def list_access_policies(self) -> list[AccessPolicyAdminResponse]:
        rows = await self._repository.list_policies()
        return [
            AccessPolicyAdminResponse(
                id=str(int(policy.id)),
                tool_id=None if policy.tool_id is None else str(int(policy.tool_id)),
                tool_name=tool_name,
                subject_type=str(policy.subject_type),
                enabled=bool(policy.enabled),
                daily_limit=None if policy.daily_limit is None else int(policy.daily_limit),
                rate_limit_per_minute=policy.rate_limit_per_minute,
                concurrency_limit=policy.concurrency_limit,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            for policy, tool_name in rows
        ]

    async def upsert_access_policy(
        self,
        *,
        tool_id: int,
        subject_type: str,
        actor_id: int,
        actor_username: str,
        payload: AccessPolicyRequest,
    ) -> AccessPolicyAdminResponse:
        tool = await self._repository.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("tool not found")
        if not subject_type:
            raise ValidationError("subject_type must not be empty")
        existing = await self._repository.policy_for(tool_id, subject_type)
        row = await self._repository.upsert_policy(
            tool_id,
            subject_type,
            enabled=payload.enabled,
            daily_limit=payload.daily_limit,
            rate_limit_per_minute=payload.rate_limit_per_minute,
            concurrency_limit=payload.concurrency_limit,
        )
        action = (
            "TOOL_ACCESS_POLICY_UPDATE" if existing is not None else "TOOL_ACCESS_POLICY_CREATE"
        )
        await self._audit.record(
            self._session,
            action=action,
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="tool_access_policy",
            resource_id=row.id,
            after_data={
                "tool_id": tool_id,
                "subject_type": subject_type,
                "enabled": payload.enabled,
                "daily_limit": payload.daily_limit,
            },
        )
        await write_operation_log(
            self._session,
            operation=action,
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="tool_access_policy",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return AccessPolicyAdminResponse(
            id=str(int(row.id)),
            tool_id=None if row.tool_id is None else str(int(row.tool_id)),
            tool_name=None if tool is None else str(tool.name),
            subject_type=str(row.subject_type),
            enabled=bool(row.enabled),
            daily_limit=None if row.daily_limit is None else int(row.daily_limit),
            rate_limit_per_minute=row.rate_limit_per_minute,
            concurrency_limit=row.concurrency_limit,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
