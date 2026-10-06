"""app.blog.authors — HTTP endpoints.

Authors are public directory data. Applying is a platform user action; reviewing
applications is an administrator action guarded by ``BLOG_AUTHOR_REVIEW``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.blog.authors.schema import (
    AuthorApplicationResponse,
    AuthorApplicationReviewRequest,
    AuthorApplyRequest,
    AuthorResponse,
)
from app.blog.authors.service import AuthorService
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


def _service(session: DbSessionDep) -> AuthorService:
    return AuthorService(session)


@router.get("/authors", response_model=ApiResponse[Page[AuthorResponse]])
async def list_authors(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: OptionalPrincipal = None,
) -> ApiResponse[Page[AuthorResponse]]:
    return success(
        await _service(session).list_authors(
            status=status, page=PageParams(page=page, page_size=page_size)
        )
    )


# Route order matters: every literal segment must be declared before the
# parameterised ``/authors/{author_id}`` or FastAPI matches it as an id and
# ``int("applications")`` raises.
@router.post(
    "/authors/apply",
    response_model=ApiResponse[AuthorApplicationResponse],
)
async def apply_author(
    payload: AuthorApplyRequest,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[AuthorApplicationResponse]:
    return success(await _service(session).apply(principal, payload))


@router.get(
    "/authors/applications",
    response_model=ApiResponse[Page[AuthorApplicationResponse]],
    dependencies=[Depends(require_permission("BLOG_AUTHOR_REVIEW"))],
)
async def list_applications(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: AdminPrincipal = None,  # noqa: ARG001
) -> ApiResponse[Page[AuthorApplicationResponse]]:
    return success(
        await _service(session).list_applications(
            status=status, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.get("/authors/{author_id}", response_model=ApiResponse[AuthorResponse])
async def get_author(
    author_id: str,
    session: DbSessionDep,
    _: OptionalPrincipal = None,
) -> ApiResponse[AuthorResponse]:
    return success(await _service(session).get_author(int(author_id)))


@router.post(
    "/authors/applications/{application_id}/review",
    response_model=ApiResponse[AuthorApplicationResponse],
    dependencies=[Depends(require_permission("BLOG_AUTHOR_REVIEW"))],
)
async def review_application(
    application_id: str,
    payload: AuthorApplicationReviewRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AuthorApplicationResponse]:
    return success(
        await _service(session).review_application(
            principal, int(application_id), payload
        )
    )
