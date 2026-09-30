"""app.blog.comments — HTTP endpoints.

Comments live under two prefixes: ``/articles/{article_id}/comments`` for the
public read and the platform user post, and ``/comments`` for moderation. The
router only receives parameters and dispatches to the service.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.blog.comments.schema import (
    CommentCreateRequest,
    CommentResponse,
    CommentReviewRequest,
)
from app.blog.comments.service import CommentService
from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    CurrentPrincipal,
    OptionalPrincipal,
    PlatformPrincipal,
    require_permission,
)
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> CommentService:
    return CommentService(session)


@router.get(
    "/articles/{article_id}/comments",
    response_model=ApiResponse[Page[CommentResponse]],
)
async def list_comments(
    article_id: str,
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: OptionalPrincipal = None,
) -> ApiResponse[Page[CommentResponse]]:
    return success(
        await _service(session).list_comments(
            int(article_id), page=PageParams(page=page, page_size=page_size)
        )
    )


@router.post(
    "/articles/{article_id}/comments",
    response_model=ApiResponse[CommentResponse],
)
async def create_comment(
    article_id: str,
    payload: CommentCreateRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[CommentResponse]:
    return success(
        await _service(session).create_comment(principal, int(article_id), payload)
    )


@router.get(
    "/pending",
    response_model=ApiResponse[Page[CommentResponse]],
    dependencies=[Depends(require_permission("BLOG_COMMENT_REVIEW"))],
)
async def pending_comments(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: AdminPrincipal = None,  # noqa: ARG001
) -> ApiResponse[Page[CommentResponse]]:
    return success(
        await _service(session).list_pending(page=PageParams(page=page, page_size=page_size))
    )


@router.delete(
    "/{comment_id}",
    response_model=ApiResponse[dict],
)
async def delete_comment(
    comment_id: str,
    session: DbSessionDep,
    principal: CurrentPrincipal,
) -> ApiResponse[dict]:
    await _service(session).delete_comment(principal, int(comment_id))
    return success({"deleted": True, "comment_id": comment_id})


@router.post(
    "/{comment_id}/review",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_permission("BLOG_COMMENT_REVIEW"))],
)
async def review_comment(
    comment_id: str,
    payload: CommentReviewRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[CommentResponse]:
    return success(
        await _service(session).review_comment(principal, int(comment_id), payload)
    )
