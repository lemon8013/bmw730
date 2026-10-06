"""app.blog.articles — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.blog.articles.schema import (
    ArticleCreateRequest,
    ArticleResponse,
    ArticleReviewRequest,
    ArticleUpdateRequest,
)
from app.blog.articles.service import ArticleService
from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    OptionalPrincipal,
    PlatformPrincipal,
    require_permission,
)
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> ArticleService:
    return ArticleService(session)


@router.get("/articles", response_model=ApiResponse[Page[ArticleResponse]])
async def list_articles(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    category_id: str | None = Query(default=None),
    author_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: OptionalPrincipal = None,
) -> ApiResponse[Page[ArticleResponse]]:
    return success(
        await _service(session).list_articles(
            keyword=keyword,
            category_id=int(category_id) if category_id else None,
            author_id=int(author_id) if author_id else None,
            status=status,
            page=PageParams(page=page, page_size=page_size),
            actor=principal,
        )
    )


@router.get(
    "/articles/review-queue",
    response_model=ApiResponse[Page[ArticleResponse]],
    dependencies=[Depends(require_permission("BLOG_ARTICLE_REVIEW"))],
)
async def review_queue(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: AdminPrincipal = None,  # noqa: ARG001
) -> ApiResponse[Page[ArticleResponse]]:
    return success(
        await _service(session).list_pending(page=PageParams(page=page, page_size=page_size))
    )


@router.get("/articles/{article_id}", response_model=ApiResponse[ArticleResponse])
async def get_article(
    article_id: str,
    session: DbSessionDep,
    _: OptionalPrincipal = None,
) -> ApiResponse[ArticleResponse]:
    return success(await _service(session).get_article(int(article_id)))


@router.get("/articles/{article_id}/tags", response_model=ApiResponse[list[str]])
async def get_article_tags(
    article_id: str,
    session: DbSessionDep,
    _: OptionalPrincipal = None,
) -> ApiResponse[list[str]]:
    return success(await _service(session).get_tags(int(article_id)))


@router.post(
    "/articles",
    response_model=ApiResponse[ArticleResponse],
)
async def create_article(
    payload: ArticleCreateRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[ArticleResponse]:
    return success(await _service(session).create_article(principal, payload))


@router.put(
    "/articles/{article_id}",
    response_model=ApiResponse[ArticleResponse],
)
async def update_article(
    article_id: str,
    payload: ArticleUpdateRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[ArticleResponse]:
    return success(
        await _service(session).update_article(principal, int(article_id), payload)
    )


@router.delete(
    "/articles/{article_id}",
    response_model=ApiResponse[dict],
)
async def delete_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[dict]:
    await _service(session).delete_article(principal, int(article_id))
    return success({"deleted": True, "article_id": article_id})


@router.post(
    "/articles/{article_id}/publish",
    response_model=ApiResponse[ArticleResponse],
)
async def publish_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[ArticleResponse]:
    return success(await _service(session).publish_article(principal, int(article_id)))


@router.post(
    "/articles/{article_id}/review",
    response_model=ApiResponse[ArticleResponse],
    dependencies=[Depends(require_permission("BLOG_ARTICLE_REVIEW"))],
)
async def review_article(
    article_id: str,
    payload: ArticleReviewRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[ArticleResponse]:
    return success(
        await _service(session).review_article(principal, int(article_id), payload)
    )
