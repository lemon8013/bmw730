"""app.admin.tools — business logic.

Management entry point for the tool catalogue and its access policies. It reuses
the platform ``tools`` models and their repositories; it does not re-implement
tool runtime behaviour (resolution, quota enforcement, execution).
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.tools.repository import AdminToolRepository
from app.admin.tools.schema import (
    AccessPolicyAdminResponse,
    AccessPolicyRequest,
    ToolCreateRequest,
    ToolStatusRequest,
    ToolUpdateRequest,
    ToolUsageAdminResponse,
    ToolUsageOverviewAdminResponse,
    ToolUsagePointAdminResponse,
    ToolUsageTrendPointAdminResponse,
    ToolVisibilityRequest,
    ToolVisibilityResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.tools.access.service import (
    SUBJECT_GUEST,
    SUBJECT_USER,
    VISIBILITY_VALUES,
    default_subject_enabled,
    visibility_of,
    visibility_subjects,
)
from app.tools.catalog.schema import ToolResponse


def _window(days: int) -> tuple[datetime.datetime, datetime.datetime]:
    """The ``[start, end)`` UTC window covering the last ``days`` calendar days.

    ``start`` is midnight UTC ``days - 1`` days ago rather than ``now - days``:
    a rolling window would spill into a partial day at both ends, so today's
    events would fall off the trend axis while still counting towards the
    totals. Aligned to midnight the window holds exactly ``days`` dates and the
    per day series adds up to the overview.
    """
    end = datetime.datetime.now(datetime.UTC)
    midnight = end.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - datetime.timedelta(days=days - 1), end


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

    async def tool_usage(self, *, days: int) -> list[ToolUsageAdminResponse]:
        """Usage counts per tool over the last ``days`` days.

        The management side has no business user identity, so it cannot call the
        platform's ``/tools/usage/*`` read model; this aggregates the raw events
        directly and is therefore independent of the daily rollup.
        """
        start, end = _window(days)
        rows = await self._repository.usage_by_tool(start=start, end=end)
        names = await self._repository.tool_names([row[0] for row in rows])
        result: list[ToolUsageAdminResponse] = []
        for tool_id, total, success, failure, users, guests, last_used in rows:
            name, slug = names.get(tool_id, (None, None))
            result.append(
                ToolUsageAdminResponse(
                    tool_id=str(tool_id),
                    tool_name=name,
                    tool_slug=slug,
                    total_count=total,
                    success_count=success,
                    failure_count=failure,
                    unique_user_count=users,
                    unique_guest_count=guests,
                    last_used_at=last_used,
                )
            )
        return result

    async def tool_usage_trend(self, *, days: int) -> list[ToolUsageTrendPointAdminResponse]:
        """Platform wide usage per day, zero filled across the whole window."""
        start, end = _window(days)
        rows = await self._repository.usage_trend(start=start, end=end)
        counts = {
            stat_date: (total, success, failure)
            for stat_date, total, success, failure in rows
        }
        result: list[ToolUsageTrendPointAdminResponse] = []
        for offset in range(days):
            stat_date = (start + datetime.timedelta(days=offset)).date()
            total, success, failure = counts.get(stat_date, (0, 0, 0))
            result.append(
                ToolUsageTrendPointAdminResponse(
                    stat_date=stat_date,
                    total_count=total,
                    success_count=success,
                    failure_count=failure,
                )
            )
        return result

    async def tool_usage_overview(self, *, days: int) -> ToolUsageOverviewAdminResponse:
        """Window wide totals for the report header cards."""
        start, end = _window(days)
        (
            total,
            success,
            failure,
            users,
            guests,
            tools,
            last_used,
        ) = await self._repository.usage_overview(start=start, end=end)
        return ToolUsageOverviewAdminResponse(
            start_date=start.date(),
            end_date=end.date(),
            total_count=total,
            success_count=success,
            failure_count=failure,
            success_rate=round(success / total * 100, 2) if total else 0.0,
            unique_user_count=users,
            unique_guest_count=guests,
            active_tool_count=tools,
            last_used_at=last_used,
        )

    async def tool_usage_daily(
        self, *, tool_id: int, days: int
    ) -> list[ToolUsagePointAdminResponse]:
        """One tool's usage per day over the last ``days`` days."""
        tool = await self._repository.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("tool not found")
        start, end = _window(days)
        rows = await self._repository.usage_daily(tool_id=tool_id, start=start, end=end)
        return [
            ToolUsagePointAdminResponse(
                stat_date=stat_date,
                total_count=total,
                success_count=success,
                failure_count=failure,
            )
            for stat_date, total, success, failure in rows
        ]

    async def list_tool_visibility(self) -> list[ToolVisibilityResponse]:
        """Every tool with the visibility its access policies resolve to."""
        rows = await self._repository.list_tools_with_policies()
        result: list[ToolVisibilityResponse] = []
        for tool, guest_policy, user_policy in rows:
            guest_enabled = (
                bool(guest_policy.enabled)
                if guest_policy is not None
                else default_subject_enabled(
                    SUBJECT_GUEST, self._settings.TOOL_DEFAULT_VISIBILITY
                )
            )
            user_enabled = (
                bool(user_policy.enabled)
                if user_policy is not None
                else default_subject_enabled(SUBJECT_USER, self._settings.TOOL_DEFAULT_VISIBILITY)
            )
            result.append(
                ToolVisibilityResponse(
                    tool_id=str(int(tool.id)),
                    tool_code=str(tool.code),
                    tool_name=str(tool.name),
                    tool_slug=str(tool.slug),
                    status=str(tool.status),
                    visibility=visibility_of(guest_enabled, user_enabled),
                    guest_enabled=guest_enabled,
                    user_enabled=user_enabled,
                    configured=guest_policy is not None or user_policy is not None,
                )
            )
        return result

    async def set_tool_visibility(
        self, *, tool_id: int, payload: ToolVisibilityRequest, actor_id: int, actor_username: str
    ) -> ToolVisibilityResponse:
        """Apply one visibility level as the tool's GUEST and USER policy rows."""
        tool = await self._repository.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("tool not found")
        visibility = str(payload.visibility or "").strip().upper()
        if visibility not in VISIBILITY_VALUES:
            raise ValidationError(
                f"visibility must be one of {', '.join(VISIBILITY_VALUES)}"
            )
        flags = visibility_subjects(visibility)
        # Snapshot before writing: the session keeps one ORM instance per row, so
        # the previous flags have to be captured as plain values first.
        before_guest = await self._repository.policy_for(tool_id, SUBJECT_GUEST)
        before_user = await self._repository.policy_for(tool_id, SUBJECT_USER)
        before = {
            "guest_enabled": None if before_guest is None else bool(before_guest.enabled),
            "user_enabled": None if before_user is None else bool(before_user.enabled),
        }
        for subject_type, enabled in flags.items():
            await self._repository.upsert_policy(tool_id, subject_type, enabled=enabled)
        guest_policy = await self._repository.policy_for(tool_id, SUBJECT_GUEST)
        user_policy = await self._repository.policy_for(tool_id, SUBJECT_USER)
        await self._audit.record(
            self._session,
            action="TOOL_VISIBILITY_CHANGE",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="tool",
            resource_id=tool_id,
            before_data=before,
            after_data={"visibility": visibility, **flags},
        )
        await write_operation_log(
            self._session,
            operation="TOOL_VISIBILITY_CHANGE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="tool",
            resource_id=str(tool_id),
        )
        await self._session.commit()
        return ToolVisibilityResponse(
            tool_id=str(int(tool.id)),
            tool_code=str(tool.code),
            tool_name=str(tool.name),
            tool_slug=str(tool.slug),
            status=str(tool.status),
            visibility=visibility,
            guest_enabled=bool(flags[SUBJECT_GUEST]),
            user_enabled=bool(flags[SUBJECT_USER]),
            configured=guest_policy is not None or user_policy is not None,
        )

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
