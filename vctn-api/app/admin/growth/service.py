"""app.admin.growth — business logic.

Why this module exists: every platform gamification endpoint is ``/me``-shaped
and resolves identity from the signed-in **business user**. The console signs in
as an operator (``sys_user``), so those endpoints answer ``401`` and an operator
can never see which user reached which level. This service exposes the same data
addressed by explicit ``user_id``.

Writing stays delegated. Growth is moved only by
:meth:`GrowthService.apply_event` and points only by
:meth:`PointService.adjust`, so the platform accounting rules (idempotency,
version locking, level recalculation, audit) keep applying to administrative
changes exactly as they do to automatic ones.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.growth.repository import AdminGrowthRepository
from app.admin.growth.schema import (
    BizUserBriefResponse,
    GrowthAccountAdminResponse,
    GrowthAdjustRequest,
    GrowthAdjustResponse,
    GrowthOverviewAdminResponse,
    GrowthRuleCreateRequest,
    GrowthRuleUpdateRequest,
    GrowthTransactionAdminResponse,
    LevelCreateRequest,
    LevelHistoryAdminResponse,
    LevelUpdateRequest,
    PointAccountAdminResponse,
    PointAdjustRequest,
    PointAdjustResponse,
    PointRuleCreateRequest,
    PointRuleUpdateRequest,
    PointTransactionAdminResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    UserAchievementAdminResponse,
    UserCosmeticAdminResponse,
    UserEquipmentAdminResponse,
    UserGrowthSummaryAdminResponse,
    UserLevelAdminResponse,
    UserTaskAdminResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.platform.achievements.repository import AchievementRepository
from app.platform.cosmetics.repository import CosmeticRepository
from app.platform.growth.model import (
    BizGrowthRule,
    BizTask,
    BizUserGrowthAccount,
    BizUserGrowthTransaction,
)
from app.platform.growth.repository import GrowthRepository
from app.platform.growth.schema import GrowthRuleResponse
from app.platform.growth.service import GrowthService
from app.platform.levels.repository import LevelRepository
from app.platform.levels.schema import LevelResponse
from app.platform.points.model import (
    BizPointRule,
    BizUserPointAccount,
)
from app.platform.points.repository import PointRepository
from app.platform.points.schema import PointRuleResponse
from app.platform.points.service import PointService
from app.platform.tasks.schema import TaskResponse
from app.platform.users.model import BizUser
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

#: `event_code` used for manual adjustments. No rule is ever seeded for it, so
#: ``GrowthService`` always awards exactly the amount the operator typed
#: instead of looking a rule up and overriding it.
ADMIN_GROWTH_EVENT_CODE: str = "ADMIN_ADJUST"

ACTIVE_LEVEL_STATUS: str = "ACTIVE"


class AdminGrowthService:
    """Administrator-facing read and adjust surface for growth and gamification."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AdminGrowthRepository(session)
        self._growth = GrowthRepository(session)
        self._points = PointRepository(session)
        self._levels = LevelRepository(session)
        self._achievements = AchievementRepository(session)
        self._cosmetics = CosmeticRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    # ------------------------------------------------------------------
    # Business users
    # ------------------------------------------------------------------
    async def list_biz_users(
        self, *, keyword: str | None, status: str | None, page: PageParams
    ) -> Page[BizUserBriefResponse]:
        rows, total = await self._repository.list_biz_users(
            keyword=keyword,
            status=status,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_user_brief(row) for row in rows], total=total, params=page
        )

    async def get_biz_user(self, user_id: int) -> BizUserBriefResponse:
        return _to_user_brief(await self._require_user(user_id))

    async def _require_user(self, user_id: int) -> BizUser:
        row = await self._repository.get_biz_user(user_id)
        if row is None:
            raise NotFoundError("business user not found")
        return row

    # ------------------------------------------------------------------
    # Growth
    # ------------------------------------------------------------------
    async def growth_account(self, user_id: int) -> GrowthAccountAdminResponse:
        user = await self._require_user(user_id)
        account_response = await GrowthService(self._session, self._settings).account(user_id)
        return GrowthAccountAdminResponse(
            user_id=account_response.user_id,
            username=user.username,
            nickname=user.nickname,
            total_growth_points=account_response.total_growth_points,
            current_level_id=account_response.current_level_id,
            current_level_name=account_response.current_level_name,
            current_level_no=account_response.current_level_no,
            next_level_id=account_response.next_level_id,
            next_level_name=account_response.next_level_name,
            next_level_points_required=account_response.next_level_points_required,
            version=account_response.version,
            updated_at=account_response.updated_at,
        )

    async def growth_transactions(
        self, user_id: int, *, page: PageParams
    ) -> Page[GrowthTransactionAdminResponse]:
        await self._require_user(user_id)
        rows, total = await self._growth.transactions(
            user_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[_to_growth_transaction(row) for row in rows],
            total=total,
            params=page,
        )

    async def adjust_growth(
        self,
        *,
        user_id: int,
        payload: GrowthAdjustRequest,
        actor_id: int,
        actor_username: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> GrowthAdjustResponse:
        """Move a growth balance by an explicit delta, always audited.

        Delegated to :meth:`GrowthService.apply_event` so the ledger entry, the
        version bump and the level recalculation happen exactly as they do for
        an automatic award.
        """
        if payload.delta_points == 0:
            raise ValidationError("the growth adjustment must not be zero")
        await self._require_user(user_id)

        before = await GrowthService(self._session, self._settings).account(user_id)
        event = await GrowthService(self._session, self._settings).apply_event(
            user_id=user_id,
            event_code=ADMIN_GROWTH_EVENT_CODE,
            growth_points=payload.delta_points,
            source_type="ADMIN",
            source_id=str(actor_id),
            reason=payload.reason,
            idempotency_key=payload.idempotency_key
            or f"admin-growth:{user_id}:{uuid.uuid4().hex}",
        )
        await self._audit.record(
            self._session,
            action="USER_GROWTH_ADJUST",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="biz_user_growth_account",
            resource_id=user_id,
            before_data={"total_growth_points": before.total_growth_points},
            after_data={
                "delta_points": payload.delta_points,
                "total_growth_points": event.total_growth_points,
                "level_changed": event.level_changed,
                "reason": payload.reason,
            },
            ip=ip,
            user_agent=user_agent,
        )
        await write_operation_log(
            self._session,
            operation="USER_GROWTH_ADJUST",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="biz_user_growth_account",
            resource_id=str(user_id),
        )
        await self._session.commit()
        transaction_id = None
        if not event.created_duplicate:
            transaction_id = await self._latest_growth_transaction_id(user_id)
        return GrowthAdjustResponse(
            user_id=str(user_id),
            delta_points=payload.delta_points,
            total_growth_points=event.total_growth_points,
            level_changed=event.level_changed,
            transaction_id=transaction_id,
        )

    async def _latest_growth_transaction_id(self, user_id: int) -> str | None:
        rows, _ = await self._growth.transactions(user_id, limit=1, offset=0)
        return str(int(rows[0].id)) if rows else None

    # ------------------------------------------------------------------
    # Growth rules
    # ------------------------------------------------------------------
    async def list_growth_rules(self, *, include_disabled: bool) -> list[GrowthRuleResponse]:
        rows = await self._growth.list_rules()
        result = [GrowthRuleResponse.model_validate(row) for row in rows]
        if include_disabled:
            return result
        return [row for row in result if row.enabled]

    async def create_growth_rule(
        self, *, payload: GrowthRuleCreateRequest, actor_id: int, actor_username: str
    ) -> GrowthRuleResponse:
        if await self._repository.rule_code_taken(BizGrowthRule, payload.rule_code):
            raise ConflictError("growth rule code already exists")
        row = await self._repository.create_rule(
            BizGrowthRule,
            rule_code=payload.rule_code,
            rule_name=payload.rule_name,
            event_code=payload.event_code,
            growth_points=payload.growth_points,
            daily_limit=payload.daily_limit,
            cooldown_seconds=payload.cooldown_seconds,
            enabled=payload.enabled,
            conditions=payload.conditions,
            description=payload.description,
        )
        await self._record(
            "GROWTH_RULE_CREATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_growth_rule",
            resource_id=int(row.id),  # type: ignore[attr-defined]
            after_data={"rule_code": payload.rule_code, "growth_points": payload.growth_points},
        )
        return GrowthRuleResponse.model_validate(row)

    async def update_growth_rule(
        self,
        *,
        rule_id: int,
        payload: GrowthRuleUpdateRequest,
        actor_id: int,
        actor_username: str,
    ) -> GrowthRuleResponse:
        row = await self._growth.get_rule(rule_id)
        if row is None:
            raise NotFoundError("growth rule not found")
        before = GrowthRuleResponse.model_validate(row).model_dump(mode="json")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        after = GrowthRuleResponse.model_validate(row).model_dump(mode="json")
        await self._record(
            "GROWTH_RULE_UPDATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_growth_rule",
            resource_id=rule_id,
            before_data=before,
            after_data=after,
        )
        return GrowthRuleResponse.model_validate(row)

    async def delete_growth_rule(
        self, *, rule_id: int, actor_id: int, actor_username: str
    ) -> None:
        row = await self._growth.get_rule(rule_id)
        if row is None:
            raise NotFoundError("growth rule not found")
        await self._repository.soft_delete_rule(row)
        await self._record(
            "GROWTH_RULE_DELETE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_growth_rule",
            resource_id=rule_id,
            before_data={"rule_code": str(row.rule_code)},
        )

    # ------------------------------------------------------------------
    # Points
    # ------------------------------------------------------------------
    async def point_account(self, user_id: int) -> PointAccountAdminResponse:
        user = await self._require_user(user_id)
        row = await PointService(self._session, self._settings).account(user_id)
        return PointAccountAdminResponse(
            user_id=row.user_id,
            username=user.username,
            nickname=user.nickname,
            balance=row.balance,
            total_earned=row.total_earned,
            total_spent=row.total_spent,
            version=row.version,
            updated_at=row.updated_at,
        )

    async def point_transactions(
        self, user_id: int, *, page: PageParams
    ) -> Page[PointTransactionAdminResponse]:
        await self._require_user(user_id)
        rows, total = await self._points.transactions(
            user_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[
                PointTransactionAdminResponse(
                    id=str(int(row.id)),
                    user_id=str(int(row.user_id)),
                    event_id=row.event_id,
                    delta_points=int(row.delta_points),
                    balance_after=int(row.balance_after),
                    transaction_type=str(row.transaction_type),
                    source_type=row.source_type,
                    source_id=row.source_id,
                    reason=row.reason,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=total,
            params=page,
        )

    async def adjust_points(
        self,
        *,
        user_id: int,
        payload: PointAdjustRequest,
        actor_id: int,
        actor_username: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> PointAdjustResponse:
        """Move a point balance by an explicit delta, always audited."""
        await self._require_user(user_id)
        result = await PointService(self._session, self._settings).adjust(
            actor_id=actor_id,
            actor_username=actor_username,
            user_id=user_id,
            delta_points=payload.delta_points,
            reason=payload.reason,
            ip=ip,
            user_agent=user_agent,
        )
        return PointAdjustResponse(
            user_id=str(user_id),
            delta_points=payload.delta_points,
            balance=result.balance,
            transaction_id=result.transaction_id,
        )

    # ------------------------------------------------------------------
    # Point rules
    # ------------------------------------------------------------------
    async def list_point_rules(self, *, include_disabled: bool) -> list[PointRuleResponse]:
        rows = await self._points.list_rules()
        result = [
            PointRuleResponse(
                id=str(int(row.id)),
                rule_code=str(row.rule_code),
                rule_name=str(row.rule_name),
                event_code=str(row.event_code),
                points=int(row.points),
                daily_limit=None if row.daily_limit is None else int(row.daily_limit),
                cooldown_seconds=row.cooldown_seconds,
                enabled=bool(row.enabled),
                conditions=row.conditions,
                description=row.description,
            )
            for row in rows
        ]
        if include_disabled:
            return result
        return [row for row in result if row.enabled]

    async def create_point_rule(
        self, *, payload: PointRuleCreateRequest, actor_id: int, actor_username: str
    ) -> PointRuleResponse:
        if await self._repository.rule_code_taken(BizPointRule, payload.rule_code):
            raise ConflictError("point rule code already exists")
        row = await self._repository.create_rule(
            BizPointRule,
            rule_code=payload.rule_code,
            rule_name=payload.rule_name,
            event_code=payload.event_code,
            points=payload.points,
            daily_limit=payload.daily_limit,
            cooldown_seconds=payload.cooldown_seconds,
            enabled=payload.enabled,
            conditions=payload.conditions,
            description=payload.description,
        )
        await self._record(
            "POINT_RULE_CREATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_point_rule",
            resource_id=int(row.id),  # type: ignore[attr-defined]
            after_data={"rule_code": payload.rule_code, "points": payload.points},
        )
        return PointRuleResponse.model_validate(row)

    async def update_point_rule(
        self,
        *,
        rule_id: int,
        payload: PointRuleUpdateRequest,
        actor_id: int,
        actor_username: str,
    ) -> PointRuleResponse:
        row = await self._points.get_rule(rule_id)
        if row is None:
            raise NotFoundError("point rule not found")
        before = PointRuleResponse.model_validate(row).model_dump(mode="json")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        after = PointRuleResponse.model_validate(row).model_dump(mode="json")
        await self._record(
            "POINT_RULE_UPDATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_point_rule",
            resource_id=rule_id,
            before_data=before,
            after_data=after,
        )
        return PointRuleResponse.model_validate(row)

    async def delete_point_rule(
        self, *, rule_id: int, actor_id: int, actor_username: str
    ) -> None:
        row = await self._points.get_rule(rule_id)
        if row is None:
            raise NotFoundError("point rule not found")
        await self._repository.soft_delete_rule(row)
        await self._record(
            "POINT_RULE_DELETE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_point_rule",
            resource_id=rule_id,
            before_data={"rule_code": str(row.rule_code)},
        )

    # ------------------------------------------------------------------
    # Levels
    # ------------------------------------------------------------------
    async def list_levels(self, *, include_disabled: bool) -> list[LevelResponse]:
        rows = await self._levels.list_levels()
        result = [LevelResponse.model_validate(row) for row in rows]
        if include_disabled:
            return result
        return [row for row in result if row.status == ACTIVE_LEVEL_STATUS]

    async def create_level(
        self, *, payload: LevelCreateRequest, actor_id: int, actor_username: str
    ) -> LevelResponse:
        if await self._repository.level_code_taken(payload.level_code):
            raise ConflictError("level code already exists")
        row = await self._repository.create_level(
            level_code=payload.level_code,
            level_name=payload.level_name,
            level_no=payload.level_no,
            min_growth_points=payload.min_growth_points,
            max_growth_points=payload.max_growth_points,
            icon_url=payload.icon_url,
            description=payload.description,
            status=payload.status,
            sort_order=payload.sort_order,
        )
        await self._record(
            "LEVEL_CREATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_user_level",
            resource_id=int(row.id),  # type: ignore[attr-defined]
            after_data={
                "level_code": payload.level_code,
                "min_growth_points": payload.min_growth_points,
            },
        )
        return LevelResponse.model_validate(row)

    async def update_level(
        self, *, level_id: int, payload: LevelUpdateRequest, actor_id: int, actor_username: str
    ) -> LevelResponse:
        from app.platform.levels.model import BizUserLevel

        row = await self._session.get(BizUserLevel, level_id)
        if row is None or row.deleted_at is not None:
            raise NotFoundError("level not found")
        before = LevelResponse.model_validate(row).model_dump(mode="json")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        after = LevelResponse.model_validate(row).model_dump(mode="json")
        await self._record(
            "LEVEL_UPDATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_user_level",
            resource_id=level_id,
            before_data=before,
            after_data=after,
        )
        return LevelResponse.model_validate(row)

    async def delete_level(
        self, *, level_id: int, actor_id: int, actor_username: str
    ) -> None:
        from app.platform.levels.model import BizUserLevel

        row = await self._session.get(BizUserLevel, level_id)
        if row is None or row.deleted_at is not None:
            raise NotFoundError("level not found")
        await self._repository.soft_delete_level(row)
        await self._record(
            "LEVEL_DELETE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_user_level",
            resource_id=level_id,
            before_data={"level_code": str(row.level_code)},
        )

    async def user_level(self, user_id: int) -> UserLevelAdminResponse:
        user = await self._require_user(user_id)
        account_response = await GrowthService(self._session, self._settings).account(user_id)
        levels = list(await self._levels.list_levels())
        current = _find_level(levels, account_response.current_level_id)
        _, change_count = await self._repository.level_history(user_id, limit=1, offset=0)
        return UserLevelAdminResponse(
            user_id=str(user_id),
            username=user.username,
            nickname=user.nickname,
            total_growth_points=account_response.total_growth_points,
            current_level_id=account_response.current_level_id,
            current_level_name=account_response.current_level_name,
            current_level_no=account_response.current_level_no,
            current_level_icon_url=None if current is None else current.icon_url,
            next_level_id=account_response.next_level_id,
            next_level_name=account_response.next_level_name,
            next_level_points_required=account_response.next_level_points_required,
            level_changed_count=change_count,
        )

    async def user_level_history(
        self, user_id: int, *, page: PageParams
    ) -> Page[LevelHistoryAdminResponse]:
        await self._require_user(user_id)
        rows, total = await self._repository.level_history(
            user_id, limit=page.limit, offset=page.offset
        )
        levels = list(await self._levels.list_levels())
        return Page.build(
            items=[
                LevelHistoryAdminResponse(
                    id=str(int(row.id)),  # type: ignore[attr-defined]
                    user_id=str(user_id),
                    from_level_id=_id_or_none(row.from_level_id),  # type: ignore[attr-defined]
                    from_level_name=_level_name(levels, row.from_level_id),  # type: ignore[attr-defined]
                    to_level_id=_id_or_none(row.to_level_id),  # type: ignore[attr-defined]
                    to_level_name=_level_name(levels, row.to_level_id),  # type: ignore[attr-defined]
                    growth_points=int(row.growth_points),  # type: ignore[attr-defined]
                    reason=row.reason,  # type: ignore[attr-defined]
                    created_at=row.created_at,  # type: ignore[attr-defined]
                )
                for row in rows
            ],
            total=total,
            params=page,
        )

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    async def list_tasks(self, *, include_disabled: bool) -> list[TaskResponse]:
        rows = await self._repository.list_tasks(include_disabled=include_disabled)
        return [TaskResponse.model_validate(row) for row in rows]

    async def get_task(self, task_id: int) -> TaskResponse:
        row = await self._repository.get_task(task_id)
        if row is None:
            raise NotFoundError("task not found")
        return TaskResponse.model_validate(row)

    async def create_task(
        self, *, payload: TaskCreateRequest, actor_id: int, actor_username: str
    ) -> TaskResponse:
        if await self._repository.task_code_taken(payload.task_code):
            raise ConflictError("task code already exists")
        row = await self._repository.create_task(
            task_code=payload.task_code,
            task_name=payload.task_name,
            task_type=payload.task_type,
            conditions=payload.conditions,
            reward=payload.reward,
            start_at=payload.start_at,
            end_at=payload.end_at,
            repeatable=payload.repeatable,
            status=payload.status,
        )
        await self._record(
            "TASK_CREATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_task",
            resource_id=int(row.id),
            after_data={"task_code": payload.task_code, "task_name": payload.task_name},
        )
        return TaskResponse.model_validate(row)

    async def update_task(
        self, *, task_id: int, payload: TaskUpdateRequest, actor_id: int, actor_username: str
    ) -> TaskResponse:
        row = await self._repository.get_task(task_id)
        if row is None:
            raise NotFoundError("task not found")
        before = TaskResponse.model_validate(row).model_dump(mode="json")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        after = TaskResponse.model_validate(row).model_dump(mode="json")
        await self._record(
            "TASK_UPDATE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_task",
            resource_id=task_id,
            before_data=before,
            after_data=after,
        )
        return TaskResponse.model_validate(row)

    async def delete_task(self, *, task_id: int, actor_id: int, actor_username: str) -> None:
        row = await self._repository.get_task(task_id)
        if row is None:
            raise NotFoundError("task not found")
        await self._repository.soft_delete_task(row)
        await self._record(
            "TASK_DELETE",
            actor_id=actor_id,
            actor_username=actor_username,
            resource_type="biz_task",
            resource_id=task_id,
            before_data={"task_code": str(row.task_code)},
        )

    async def user_tasks(self, user_id: int) -> list[UserTaskAdminResponse]:
        """Every task the user started, with the definition merged in."""
        await self._require_user(user_id)
        rows = await self._repository.user_tasks_with_definition(user_id)
        result: list[UserTaskAdminResponse] = []
        for user_task, task in rows:
            progress: dict[str, Any] = dict(user_task.progress or {})
            conditions: dict[str, Any] = dict(task.conditions or {}) if task is not None else {}
            target = conditions.get("target_count")
            result.append(
                UserTaskAdminResponse(
                    id=str(int(user_task.id)),
                    user_id=str(user_id),
                    task_id=str(int(user_task.task_id or 0)),
                    task_code=None if task is None else str(task.task_code),
                    task_name=None if task is None else str(task.task_name),
                    task_type=None if task is None else str(task.task_type),
                    target_count=int(target) if target is not None else None,
                    current_count=int(progress.get("count", 0)),
                    status=str(user_task.status),
                    completed_at=user_task.completed_at,
                    reward_claimed=bool(progress.get("reward_claimed", False)),
                    reward=dict(task.reward or {}) if task is not None else None,
                    created_at=user_task.created_at,
                    updated_at=user_task.updated_at,
                )
            )
        return result

    # ------------------------------------------------------------------
    # Achievements & cosmetics
    # ------------------------------------------------------------------
    async def user_achievements(self, user_id: int) -> list[UserAchievementAdminResponse]:
        """Every achievement, flagged with whether this user unlocked it."""
        await self._require_user(user_id)
        definitions = await self._repository.all_achievements()
        unlocked = await self._repository.unlocked_map(user_id)
        result: list[UserAchievementAdminResponse] = []
        for row in definitions:
            achievement_id = int(row.id)  # type: ignore[attr-defined]
            achieved_at = unlocked.get(achievement_id)
            result.append(
                UserAchievementAdminResponse(
                    achievement_id=str(achievement_id),
                    achievement_code=str(row.achievement_code),  # type: ignore[attr-defined]
                    achievement_name=str(row.achievement_name),  # type: ignore[attr-defined]
                    conditions=row.conditions,  # type: ignore[attr-defined]
                    reward=row.reward,  # type: ignore[attr-defined]
                    status=str(row.status),  # type: ignore[attr-defined]
                    unlocked=achieved_at is not None,
                    achieved_at=achieved_at,
                )
            )
        return result

    async def user_cosmetics(self, user_id: int) -> list[UserCosmeticAdminResponse]:
        """Every cosmetic, flagged with whether this user owns it."""
        await self._require_user(user_id)
        definitions = await self._repository.all_cosmetics()
        owned = await self._repository.owned_map(user_id)
        result: list[UserCosmeticAdminResponse] = []
        for row in definitions:
            cosmetic_id = int(row.id)  # type: ignore[attr-defined]
            obtained_at, source_type = owned.get(cosmetic_id, (None, None))
            result.append(
                UserCosmeticAdminResponse(
                    cosmetic_id=str(cosmetic_id),
                    cosmetic_code=str(row.cosmetic_code),  # type: ignore[attr-defined]
                    cosmetic_name=str(row.cosmetic_name),  # type: ignore[attr-defined]
                    cosmetic_type=str(row.cosmetic_type),  # type: ignore[attr-defined]
                    asset_url=row.asset_url,  # type: ignore[attr-defined]
                    sort_order=int(row.sort_order or 0),  # type: ignore[attr-defined]
                    owned=obtained_at is not None,
                    obtained_at=obtained_at,
                    source_type=source_type,
                )
            )
        return result

    async def user_equipment(self, user_id: int) -> UserEquipmentAdminResponse:
        await self._require_user(user_id)
        row = await self._repository.equipment(user_id)
        names = await self._cosmetic_names()
        slots = (
            ("avatar_cosmetic_id", "avatar_cosmetic_name"),
            ("avatar_frame_cosmetic_id", "avatar_frame_cosmetic_name"),
            ("crown_cosmetic_id", "crown_cosmetic_name"),
            ("badge_cosmetic_id", "badge_cosmetic_name"),
            ("title_cosmetic_id", "title_cosmetic_name"),
            ("name_effect_cosmetic_id", "name_effect_cosmetic_name"),
        )
        payload: dict[str, Any] = {"user_id": str(user_id)}
        for id_field, name_field in slots:
            raw = getattr(row, id_field, None) if row is not None else None
            payload[id_field] = None if raw is None else str(int(raw))
            payload[name_field] = names.get(int(raw)) if raw is not None else None
        return UserEquipmentAdminResponse(**payload)

    async def _cosmetic_names(self) -> dict[int, str]:
        return {
            int(row.id): str(row.cosmetic_name)  # type: ignore[attr-defined]
            for row in await self._repository.all_cosmetics()
        }

    # ------------------------------------------------------------------
    # Cross-module summary
    # ------------------------------------------------------------------
    async def summary(self, user_id: int) -> UserGrowthSummaryAdminResponse:
        """One user's whole gamification footprint in a single round trip."""
        user = await self._require_user(user_id)
        growth = await self.growth_account(user_id)
        points = await self.point_account(user_id)
        level = await self.user_level(user_id)
        tasks = await self.user_tasks(user_id)
        achievements = await self.user_achievements(user_id)
        cosmetics = await self.user_cosmetics(user_id)
        return UserGrowthSummaryAdminResponse(
            user=_to_user_brief(user),
            growth=growth,
            points=points,
            level=level,
            task_total=len(tasks),
            task_completed=sum(1 for row in tasks if row.status == "COMPLETED"),
            task_reward_claimed=sum(1 for row in tasks if row.reward_claimed),
            achievement_total=len(achievements),
            achievement_unlocked=sum(1 for row in achievements if row.unlocked),
            cosmetic_total=len(cosmetics),
            cosmetic_owned=sum(1 for row in cosmetics if row.owned),
        )

    async def overview(self) -> GrowthOverviewAdminResponse:
        from app.platform.cosmetics.model import BizCosmetic
        from app.platform.growth.model import (
            BizAchievement,
            BizUserAchievement,
            BizUserTask,
        )
        from app.platform.levels.model import BizUserLevel

        return GrowthOverviewAdminResponse(
            biz_user_count=await self._repository.count_rows(BizUser),
            growth_account_count=await self._repository.count_rows(
                BizUserGrowthAccount, column=BizUserGrowthAccount.user_id
            ),
            total_growth_points=await self._repository.sum_column(
                BizUserGrowthAccount.total_growth_points
            ),
            point_account_count=await self._repository.count_rows(
                BizUserPointAccount, column=BizUserPointAccount.user_id
            ),
            total_point_balance=await self._repository.sum_column(BizUserPointAccount.balance),
            user_task_count=await self._repository.count_rows(BizUserTask),
            user_task_completed=await self._repository.count_rows_where(
                BizUserTask, BizUserTask.status == "COMPLETED"
            ),
            user_task_reward_claimed=await self._claim_count(),
            user_achievement_count=await self._repository.count_rows(BizUserAchievement),
            growth_rule_count=await self._repository.count_rows_where(
                BizGrowthRule, BizGrowthRule.deleted_at.is_(None)
            ),
            growth_rule_enabled=await self._repository.count_rows_where(
                BizGrowthRule,
                BizGrowthRule.deleted_at.is_(None),
                BizGrowthRule.enabled.is_(True),
            ),
            point_rule_count=await self._repository.count_rows_where(
                BizPointRule, BizPointRule.deleted_at.is_(None)
            ),
            point_rule_enabled=await self._repository.count_rows_where(
                BizPointRule,
                BizPointRule.deleted_at.is_(None),
                BizPointRule.enabled.is_(True),
            ),
            task_count=await self._repository.count_rows_where(
                BizTask, BizTask.deleted_at.is_(None)
            ),
            achievement_count=await self._repository.count_rows_where(
                BizAchievement, BizAchievement.deleted_at.is_(None)
            ),
            level_count=await self._repository.count_rows_where(
                BizUserLevel, BizUserLevel.deleted_at.is_(None)
            ),
            cosmetic_count=await self._repository.count_rows_where(
                BizCosmetic, BizCosmetic.deleted_at.is_(None)
            ),
        )

    async def _claim_count(self) -> int:
        """Count user tasks whose ``progress.reward_claimed`` flag is true."""
        from sqlalchemy import func, select

        from app.platform.growth.model import BizUserTask

        # ``reward_claimed`` lives inside the JSONB progress column, so the count
        # needs a JSON accessor rather than a plain column predicate.
        claimed = BizUserTask.progress["reward_claimed"].as_string()
        return int(
            (
                await self._session.execute(
                    select(func.count(BizUserTask.id)).where(claimed == "true")
                )
            ).scalar_one()
        )

    # ------------------------------------------------------------------
    # Shared write helpers
    # ------------------------------------------------------------------
    async def _record(
        self,
        action: str,
        *,
        actor_id: int,
        actor_username: str,
        resource_type: str,
        resource_id: int,
        before_data: dict | None = None,
        after_data: dict | None = None,
    ) -> None:
        await self._audit.record(
            self._session,
            action=action,
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type=resource_type,
            resource_id=resource_id,
            before_data=before_data or {},
            after_data=after_data or {},
        )
        await write_operation_log(
            self._session,
            operation=action,
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type=resource_type,
            resource_id=str(resource_id),
        )
        await self._session.commit()


# ---------------------------------------------------------------------------
# Module level helpers
# ---------------------------------------------------------------------------


def _to_user_brief(row: BizUser) -> BizUserBriefResponse:
    return BizUserBriefResponse(
        user_id=str(int(row.id)),
        username=row.username,
        nickname=row.nickname,
        email=row.email,
        status=str(row.status),
        registered_at=row.registered_at,
        last_login_at=row.last_login_at,
    )


def _to_growth_transaction(row: BizUserGrowthTransaction) -> GrowthTransactionAdminResponse:
    return GrowthTransactionAdminResponse(
        id=str(int(row.id)),
        user_id=str(int(row.user_id or 0)),
        event_id=None if row.event_id is None else str(row.event_id),
        delta_points=int(row.delta_points),
        balance_after=int(row.balance_after),
        transaction_type=str(row.transaction_type),
        reason=row.reason,
        created_at=row.created_at,
    )


def _find_level(levels: list[object], level_id: object | None) -> LevelResponse | None:
    if level_id is None:
        return None
    for row in levels:
        if int(row.id) == int(level_id):  # type: ignore[attr-defined]
            return LevelResponse.model_validate(row)
    return None


def _level_name(levels: list[object], level_id: object | None) -> str | None:
    row = _find_level(levels, level_id)
    return None if row is None else row.level_name


def _id_or_none(value: object | None) -> str | None:
    return None if value is None else str(int(value))  # type: ignore[arg-type]


__all__ = ["ADMIN_GROWTH_EVENT_CODE", "AdminGrowthService"]
