"""app.admin.tools — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.tools.schema import (
    AccessPolicyAdminResponse,
    AccessPolicyRequest,
    ToolCategoryCreateRequest,
    ToolCategoryUpdateRequest,
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
from app.admin.tools.service import AdminToolService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.catalog.schema import ToolCategoryResponse, ToolResponse

router = APIRouter()


@router.get("/tools/categories", response_model=ApiResponse[list[ToolCategoryResponse]])
async def list_tool_categories(
    session: DbSessionDep,
    include_disabled: bool = Query(default=True),
    principal: Principal = Depends(require_permission("TOOL_CATEGORY_VIEW")),
) -> ApiResponse[list[ToolCategoryResponse]]:
    return success(
        await AdminToolService(session).list_categories(include_disabled=include_disabled)
    )


@router.post("/tools/categories", response_model=ApiResponse[ToolCategoryResponse])
async def create_tool_category(
    payload: ToolCategoryCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_CATEGORY_EDIT")),
) -> ApiResponse[ToolCategoryResponse]:
    return success(
        await AdminToolService(session).create_category(
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.put(
    "/tools/categories/{category_id}", response_model=ApiResponse[ToolCategoryResponse]
)
async def update_tool_category(
    category_id: str,
    payload: ToolCategoryUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_CATEGORY_EDIT")),
) -> ApiResponse[ToolCategoryResponse]:
    return success(
        await AdminToolService(session).update_category(
            category_id=int(category_id),
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.delete("/tools/categories/{category_id}", response_model=ApiResponse[None])
async def delete_tool_category(
    category_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_CATEGORY_EDIT")),
) -> ApiResponse[None]:
    await AdminToolService(session).delete_category(
        category_id=int(category_id),
        actor_id=principal.subject_id,
        actor_username=principal.username,
    )
    return success(None)


@router.get("/tools", response_model=ApiResponse[Page[ToolResponse]])
async def list_tools(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    category_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("TOOL_VIEW")),
) -> ApiResponse[Page[ToolResponse]]:
    return success(
        await AdminToolService(session).list_tools(
            status=status,
            category_id=int(category_id) if category_id else None,
            keyword=keyword,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post("/tools", response_model=ApiResponse[ToolResponse])
async def create_tool(
    payload: ToolCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_MANAGE")),
) -> ApiResponse[ToolResponse]:
    return success(
        await AdminToolService(session).create_tool(
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


# The literal ``/tools/access-policies`` path must be declared before
# ``/tools/{tool_id}``: FastAPI matches routes in registration order, so a
# parameterised route declared first would swallow it and try to parse
# "access-policies" as an integer id.
# The literal ``/tools/visibility`` and ``/tools/usage`` paths must be declared
# before ``/tools/{tool_id}``: FastAPI matches routes in registration order, so a
# parameterised route declared first would swallow them and try to parse the
# literal segment as an integer id.
@router.get("/tools/usage", response_model=ApiResponse[list[ToolUsageAdminResponse]])
async def list_tool_usage(
    session: DbSessionDep,
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require_permission("TOOL_STAT_VIEW")),
) -> ApiResponse[list[ToolUsageAdminResponse]]:
    return success(await AdminToolService(session).tool_usage(days=days))


@router.get(
    "/tools/usage/overview", response_model=ApiResponse[ToolUsageOverviewAdminResponse]
)
async def tool_usage_overview(
    session: DbSessionDep,
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require_permission("TOOL_STAT_VIEW")),
) -> ApiResponse[ToolUsageOverviewAdminResponse]:
    return success(await AdminToolService(session).tool_usage_overview(days=days))


@router.get(
    "/tools/usage/trend", response_model=ApiResponse[list[ToolUsageTrendPointAdminResponse]]
)
async def tool_usage_trend(
    session: DbSessionDep,
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require_permission("TOOL_STAT_VIEW")),
) -> ApiResponse[list[ToolUsageTrendPointAdminResponse]]:
    return success(await AdminToolService(session).tool_usage_trend(days=days))


@router.get("/tools/usage/daily", response_model=ApiResponse[list[ToolUsagePointAdminResponse]])
async def tool_usage_daily(
    session: DbSessionDep,
    tool_id: str = Query(),
    days: int = Query(default=30, ge=1, le=365),
    principal: Principal = Depends(require_permission("TOOL_STAT_VIEW")),
) -> ApiResponse[list[ToolUsagePointAdminResponse]]:
    return success(
        await AdminToolService(session).tool_usage_daily(tool_id=int(tool_id), days=days)
    )


@router.get("/tools/visibility", response_model=ApiResponse[list[ToolVisibilityResponse]])
async def list_tool_visibility(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_VIEW")),
) -> ApiResponse[list[ToolVisibilityResponse]]:
    return success(await AdminToolService(session).list_tool_visibility())


@router.put(
    "/tools/visibility/{tool_id}", response_model=ApiResponse[ToolVisibilityResponse]
)
async def set_tool_visibility(
    tool_id: str,
    payload: ToolVisibilityRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_ACCESS_MANAGE")),
) -> ApiResponse[ToolVisibilityResponse]:
    return success(
        await AdminToolService(session).set_tool_visibility(
            tool_id=int(tool_id),
            payload=payload,
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.get("/tools/access-policies", response_model=ApiResponse[list[AccessPolicyAdminResponse]])
async def list_access_policies(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_VIEW")),
) -> ApiResponse[list[AccessPolicyAdminResponse]]:
    return success(await AdminToolService(session).list_access_policies())


@router.put(
    "/tools/access-policies/{tool_id}",
    response_model=ApiResponse[AccessPolicyAdminResponse],
)
async def upsert_access_policy(
    tool_id: str,
    payload: AccessPolicyRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_MANAGE")),
) -> ApiResponse[AccessPolicyAdminResponse]:
    return success(
        await AdminToolService(session).upsert_access_policy(
            tool_id=int(tool_id),
            subject_type=payload.subject_type,
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.get("/tools/{tool_id}", response_model=ApiResponse[ToolResponse])
async def get_tool(
    tool_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_VIEW")),
) -> ApiResponse[ToolResponse]:
    return success(await AdminToolService(session).get_tool(int(tool_id)))


@router.put("/tools/{tool_id}", response_model=ApiResponse[ToolResponse])
async def update_tool(
    tool_id: str,
    payload: ToolUpdateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_MANAGE")),
) -> ApiResponse[ToolResponse]:
    return success(
        await AdminToolService(session).update_tool(
            tool_id=int(tool_id),
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.put("/tools/{tool_id}/status", response_model=ApiResponse[ToolResponse])
async def set_tool_status(
    tool_id: str,
    payload: ToolStatusRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TOOL_MANAGE")),
) -> ApiResponse[ToolResponse]:
    return success(
        await AdminToolService(session).set_status(
            tool_id=int(tool_id),
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )
