"""app.admin.growth — HTTP endpoints.

Every platform gamification endpoint is ``/me``-shaped and answers ``401`` for
an operator, so the console needs this operator-facing surface that addresses
data by explicit ``user_id`` instead.

**Route order matters**: FastAPI matches in registration order, so the literal
``/growth/...``, ``/points/...``, ``/levels`` and ``/tasks`` paths must all be
declared **before** any ``/users/{user_id}/...`` parameterised route that could
otherwise swallow them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

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
from app.admin.growth.service import AdminGrowthService
from app.core.dependencies import DbSessionDep
from app.platform.growth.schema import GrowthRuleResponse
from app.platform.levels.schema import LevelResponse
from app.platform.points.schema import PointRuleResponse
from app.platform.tasks.schema import TaskResponse
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AdminGrowthService:
    return AdminGrowthService(session)


def _page(page: int, page_size: int) -> PageParams:
    return PageParams(page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Overview  (declared first: it sits under the same ``/growth`` segment)
# ---------------------------------------------------------------------------


@router.get("/growth/overview", response_model=ApiResponse[GrowthOverviewAdminResponse])
async def growth_overview(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_VIEW")),
) -> ApiResponse[GrowthOverviewAdminResponse]:
    return success(await _service(session).overview())


# ---------------------------------------------------------------------------
# Business users
# ---------------------------------------------------------------------------


@router.get("/biz-users", response_model=ApiResponse[Page[BizUserBriefResponse]])
async def list_biz_users(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("BIZ_USER_VIEW")),
) -> ApiResponse[Page[BizUserBriefResponse]]:
    return success(
        await _service(session).list_biz_users(
            keyword=keyword, status=status, page=_page(page, page_size)
        )
    )


# ---------------------------------------------------------------------------
# Growth rules
# ---------------------------------------------------------------------------


@router.get("/growth/rules", response_model=ApiResponse[list[GrowthRuleResponse]])
async def list_growth_rules(
    session: DbSessionDep,
    include_disabled: bool = Query(default=True),
    principal: Principal = Depends(require_permission("GROWTH_RULE_VIEW")),
) -> ApiResponse[list[GrowthRuleResponse]]:
    return success(await _service(session).list_growth_rules(include_disabled=include_disabled))


@router.post("/growth/rules", response_model=ApiResponse[GrowthRuleResponse])
async def create_growth_rule(
    payload: GrowthRuleCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_EDIT")),
) -> ApiResponse[GrowthRuleResponse]:
    return success(
        await _service(session).create_growth_rule(
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.put("/growth/rules/{rule_id}", response_model=ApiResponse[GrowthRuleResponse])
async def update_growth_rule(
    rule_id: str,
    payload: GrowthRuleUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_EDIT")),
) -> ApiResponse[GrowthRuleResponse]:
    return success(
        await _service(session).update_growth_rule(
            rule_id=int(rule_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.delete("/growth/rules/{rule_id}", response_model=ApiResponse[dict])
async def delete_growth_rule(
    rule_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_EDIT")),
) -> ApiResponse[dict]:
    await _service(session).delete_growth_rule(
        rule_id=int(rule_id),
        actor_id=principal.subject_id,
        actor_username=principal.username,
    )
    return success({"rule_id": rule_id, "deleted": True})


# ---------------------------------------------------------------------------
# Point rules
# ---------------------------------------------------------------------------


@router.get("/points/rules", response_model=ApiResponse[list[PointRuleResponse]])
async def list_point_rules(
    session: DbSessionDep,
    include_disabled: bool = Query(default=True),
    principal: Principal = Depends(require_permission("POINT_RULE_VIEW")),
) -> ApiResponse[list[PointRuleResponse]]:
    return success(await _service(session).list_point_rules(include_disabled=include_disabled))


@router.post("/points/rules", response_model=ApiResponse[PointRuleResponse])
async def create_point_rule(
    payload: PointRuleCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("POINT_RULE_EDIT")),
) -> ApiResponse[PointRuleResponse]:
    return success(
        await _service(session).create_point_rule(
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.put("/points/rules/{rule_id}", response_model=ApiResponse[PointRuleResponse])
async def update_point_rule(
    rule_id: str,
    payload: PointRuleUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("POINT_RULE_EDIT")),
) -> ApiResponse[PointRuleResponse]:
    return success(
        await _service(session).update_point_rule(
            rule_id=int(rule_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.delete("/points/rules/{rule_id}", response_model=ApiResponse[dict])
async def delete_point_rule(
    rule_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("POINT_RULE_EDIT")),
) -> ApiResponse[dict]:
    await _service(session).delete_point_rule(
        rule_id=int(rule_id),
        actor_id=principal.subject_id,
        actor_username=principal.username,
    )
    return success({"rule_id": rule_id, "deleted": True})


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------


@router.get("/levels", response_model=ApiResponse[list[LevelResponse]])
async def list_levels(
    session: DbSessionDep,
    include_disabled: bool = Query(default=True),
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_VIEW")),
) -> ApiResponse[list[LevelResponse]]:
    return success(await _service(session).list_levels(include_disabled=include_disabled))


@router.post("/levels", response_model=ApiResponse[LevelResponse])
async def create_level(
    payload: LevelCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_EDIT")),
) -> ApiResponse[LevelResponse]:
    return success(
        await _service(session).create_level(
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.put("/levels/{level_id}", response_model=ApiResponse[LevelResponse])
async def update_level(
    level_id: str,
    payload: LevelUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_EDIT")),
) -> ApiResponse[LevelResponse]:
    return success(
        await _service(session).update_level(
            level_id=int(level_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.delete("/levels/{level_id}", response_model=ApiResponse[dict])
async def delete_level(
    level_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_EDIT")),
) -> ApiResponse[dict]:
    """Retire a level. Levels are never physically deleted."""
    await _service(session).delete_level(
        level_id=int(level_id),
        actor_id=principal.subject_id,
        actor_username=principal.username,
    )
    return success({"level_id": level_id, "deleted": True})


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.get("/tasks", response_model=ApiResponse[list[TaskResponse]])
async def list_tasks(
    session: DbSessionDep,
    include_disabled: bool = Query(default=True),
    principal: Principal = Depends(require_permission("TASK_CONFIG_VIEW")),
) -> ApiResponse[list[TaskResponse]]:
    return success(await _service(session).list_tasks(include_disabled=include_disabled))


@router.post("/tasks", response_model=ApiResponse[TaskResponse])
async def create_task(
    payload: TaskCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TASK_CONFIG_EDIT")),
) -> ApiResponse[TaskResponse]:
    return success(
        await _service(session).create_task(
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.put("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
async def update_task(
    task_id: str,
    payload: TaskUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TASK_CONFIG_EDIT")),
) -> ApiResponse[TaskResponse]:
    return success(
        await _service(session).update_task(
            task_id=int(task_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.delete("/tasks/{task_id}", response_model=ApiResponse[dict])
async def delete_task(
    task_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TASK_CONFIG_EDIT")),
) -> ApiResponse[dict]:
    """Retire a task definition. Tasks are never physically deleted."""
    await _service(session).delete_task(
        task_id=int(task_id),
        actor_id=principal.subject_id,
        actor_username=principal.username,
    )
    return success({"task_id": task_id, "deleted": True})


# ---------------------------------------------------------------------------
# Per-user views  (declared last: ``/users/{user_id}`` is parameterised)
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}/summary", response_model=ApiResponse[UserGrowthSummaryAdminResponse])
async def user_growth_summary(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_VIEW")),
) -> ApiResponse[UserGrowthSummaryAdminResponse]:
    return success(await _service(session).summary(int(user_id)))


@router.get("/users/{user_id}/growth", response_model=ApiResponse[GrowthAccountAdminResponse])
async def user_growth_account(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("GROWTH_RULE_VIEW")),
) -> ApiResponse[GrowthAccountAdminResponse]:
    return success(await _service(session).growth_account(int(user_id)))


@router.get(
    "/users/{user_id}/growth/transactions",
    response_model=ApiResponse[Page[GrowthTransactionAdminResponse]],
)
async def user_growth_transactions(
    user_id: str,
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("GROWTH_RULE_VIEW")),
) -> ApiResponse[Page[GrowthTransactionAdminResponse]]:
    return success(
        await _service(session).growth_transactions(
            int(user_id), page=_page(page, page_size)
        )
    )


@router.post(
    "/users/{user_id}/growth/adjust", response_model=ApiResponse[GrowthAdjustResponse]
)
async def adjust_user_growth(
    user_id: str,
    payload: GrowthAdjustRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_GROWTH_ADJUST")),
) -> ApiResponse[GrowthAdjustResponse]:
    return success(
        await _service(session).adjust_growth(
            user_id=int(user_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
    )


@router.get("/users/{user_id}/points", response_model=ApiResponse[PointAccountAdminResponse])
async def user_point_account(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("POINT_RULE_VIEW")),
) -> ApiResponse[PointAccountAdminResponse]:
    return success(await _service(session).point_account(int(user_id)))


@router.get(
    "/users/{user_id}/points/transactions",
    response_model=ApiResponse[Page[PointTransactionAdminResponse]],
)
async def user_point_transactions(
    user_id: str,
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("POINT_RULE_VIEW")),
) -> ApiResponse[Page[PointTransactionAdminResponse]]:
    return success(
        await _service(session).point_transactions(int(user_id), page=_page(page, page_size))
    )


@router.post("/users/{user_id}/points/adjust", response_model=ApiResponse[PointAdjustResponse])
async def adjust_user_points(
    user_id: str,
    payload: PointAdjustRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("USER_POINT_ADJUST")),
) -> ApiResponse[PointAdjustResponse]:
    return success(
        await _service(session).adjust_points(
            user_id=int(user_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
    )


@router.get("/users/{user_id}/levels", response_model=ApiResponse[UserLevelAdminResponse])
async def user_level(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_VIEW")),
) -> ApiResponse[UserLevelAdminResponse]:
    return success(await _service(session).user_level(int(user_id)))


@router.get(
    "/users/{user_id}/levels/history",
    response_model=ApiResponse[Page[LevelHistoryAdminResponse]],
)
async def user_level_history(
    user_id: str,
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("LEVEL_CONFIG_VIEW")),
) -> ApiResponse[Page[LevelHistoryAdminResponse]]:
    return success(
        await _service(session).user_level_history(int(user_id), page=_page(page, page_size))
    )


@router.get("/users/{user_id}/tasks", response_model=ApiResponse[list[UserTaskAdminResponse]])
async def user_tasks(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TASK_CONFIG_VIEW")),
) -> ApiResponse[list[UserTaskAdminResponse]]:
    return success(await _service(session).user_tasks(int(user_id)))


@router.get(
    "/users/{user_id}/achievements",
    response_model=ApiResponse[list[UserAchievementAdminResponse]],
)
async def user_achievements(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("ACHIEVEMENT_CONFIG_VIEW")),
) -> ApiResponse[list[UserAchievementAdminResponse]]:
    return success(await _service(session).user_achievements(int(user_id)))


@router.get(
    "/users/{user_id}/cosmetics",
    response_model=ApiResponse[list[UserCosmeticAdminResponse]],
)
async def user_cosmetics(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("COSMETIC_VIEW")),
) -> ApiResponse[list[UserCosmeticAdminResponse]]:
    return success(await _service(session).user_cosmetics(int(user_id)))


@router.get(
    "/users/{user_id}/cosmetics/equipment",
    response_model=ApiResponse[UserEquipmentAdminResponse],
)
async def user_equipment(
    user_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("COSMETIC_VIEW")),
) -> ApiResponse[UserEquipmentAdminResponse]:
    return success(await _service(session).user_equipment(int(user_id)))
