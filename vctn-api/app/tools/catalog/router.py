"""app.tools.catalog — public HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import OptionalPrincipal, PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.catalog.schema import (
    PopularToolResponse,
    RecentToolResponse,
    ToolCategoryResponse,
    ToolResponse,
)
from app.tools.catalog.service import ToolCatalogService

router = APIRouter()


def _service(session: DbSessionDep) -> ToolCatalogService:
    return ToolCatalogService(session)


@router.get("/tool-categories", response_model=ApiResponse[list[ToolCategoryResponse]])
async def list_categories(session: DbSessionDep) -> ApiResponse[list[ToolCategoryResponse]]:
    return success(await _service(session).categories())


@router.get("/tools/popular", response_model=ApiResponse[list[PopularToolResponse]])
async def popular_tools(
    session: DbSessionDep,
    principal: OptionalPrincipal,
    window_days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[PopularToolResponse]]:
    rows = await _service(session).popular(
        window_days=window_days, limit=limit, is_guest=principal is None
    )
    return success([PopularToolResponse.model_validate(row) for row in rows])


@router.get("/tools/recent", response_model=ApiResponse[list[RecentToolResponse]])
async def recent_tools(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[RecentToolResponse]]:
    rows = await _service(session).recent(principal.subject_id, limit=limit)
    return success([RecentToolResponse.model_validate(row) for row in rows])


@router.get("/tools/search", response_model=ApiResponse[list[ToolResponse]])
async def search_tools(
    session: DbSessionDep,
    principal: OptionalPrincipal,
    keyword: str = Query(min_length=1, max_length=128),
) -> ApiResponse[list[ToolResponse]]:
    return success(await _service(session).search(keyword, is_guest=principal is None))


@router.get("/tools/by-slug/{slug}", response_model=ApiResponse[ToolResponse])
async def tool_by_slug(
    slug: str, session: DbSessionDep, principal: OptionalPrincipal
) -> ApiResponse[ToolResponse]:
    return success(await _service(session).get_by_slug(slug, is_guest=principal is None))


@router.get("/tools", response_model=ApiResponse[list[ToolResponse]])
async def list_tools(
    session: DbSessionDep,
    principal: OptionalPrincipal,
    category_id: str | None = Query(default=None),
) -> ApiResponse[list[ToolResponse]]:
    return success(
        await _service(session).list_tools(
            int(category_id) if category_id else None, is_guest=principal is None
        )
    )


@router.get("/tools/{tool_id}", response_model=ApiResponse[ToolResponse])
async def get_tool(
    tool_id: str, session: DbSessionDep, principal: OptionalPrincipal
) -> ApiResponse[ToolResponse]:
    return success(await _service(session).get_tool(int(tool_id), is_guest=principal is None))
