"""app.blog.categories — HTTP endpoints.

Category management is an administrator responsibility, so every write endpoint
is guarded by ``AdminPrincipal`` + a ``BLOG_CATEGORY_MANAGE`` permission. The
read endpoints are public so the content UI can render the category tree.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.blog.categories.schema import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.blog.categories.service import CategoryService
from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    OptionalPrincipal,
    require_permission,
)
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> CategoryService:
    return CategoryService(session)


@router.get("/categories", response_model=ApiResponse[Page[CategoryResponse]])
async def list_categories(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: OptionalPrincipal = None,
) -> ApiResponse[Page[CategoryResponse]]:
    return success(
        await _service(session).list_categories(
            keyword=keyword,
            status=status,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/categories/{category_id}", response_model=ApiResponse[CategoryResponse])
async def get_category(
    category_id: str,
    session: DbSessionDep,
    _: OptionalPrincipal = None,
) -> ApiResponse[CategoryResponse]:
    return success(await _service(session).get_category(int(category_id)))


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryResponse],
    dependencies=[Depends(require_permission("BLOG_CATEGORY_MANAGE"))],
)
async def create_category(
    payload: CategoryCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[CategoryResponse]:
    return success(await _service(session).create_category(principal, payload))


@router.put(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryResponse],
    dependencies=[Depends(require_permission("BLOG_CATEGORY_MANAGE"))],
)
async def update_category(
    category_id: str,
    payload: CategoryUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[CategoryResponse]:
    return success(
        await _service(session).update_category(principal, int(category_id), payload)
    )


@router.delete(
    "/categories/{category_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("BLOG_CATEGORY_MANAGE"))],
)
async def delete_category(
    category_id: str,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[dict]:
    await _service(session).delete_category(principal, int(category_id))
    return success({"deleted": True, "category_id": category_id})
