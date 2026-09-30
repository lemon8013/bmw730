"""app.admin.tools — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.tools.schema import (
    AccessPolicyAdminResponse,
    AccessPolicyRequest,
    ToolCreateRequest,
    ToolStatusRequest,
    ToolUpdateRequest,
)
from app.admin.tools.service import AdminToolService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.catalog.schema import ToolResponse

router = APIRouter()


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
