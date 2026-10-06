"""app.blog.authors — business logic.

Becoming an author is an application gated by an admin review. Once approved the
author profile is created (or activated) and the platform user may publish
articles.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.authors.model import BlogAuthor, BlogAuthorApplication
from app.blog.authors.repository import AuthorRepository
from app.blog.authors.schema import (
    AuthorApplicationResponse,
    AuthorApplicationReviewRequest,
    AuthorApplyRequest,
    AuthorResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class AuthorService:
    """Author and author-application management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AuthorRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_authors(
        self, *, status: str | None = None, page: PageParams
    ) -> Page[AuthorResponse]:
        rows, total = await self._repository.list_authors(
            status=status, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_author(row) for row in rows], total=total, params=page
        )

    async def get_author(self, author_id: int) -> AuthorResponse:
        row = await self._repository.get(author_id)
        if row is None:
            raise NotFoundError("author not found")
        return self._to_author(row)

    async def apply(
        self, actor: Principal, payload: AuthorApplyRequest
    ) -> AuthorApplicationResponse:
        if await self._repository.get_by_user_id(actor.subject_id):
            raise ConflictError("you are already an author")
        existing = await self._repository.get_application_by_user(actor.subject_id)
        if existing is not None and existing.status == "PENDING":
            raise ConflictError("an application is already pending review")
        now = datetime.datetime.now(datetime.UTC)
        await self._repository.create_author(
            id=new_id(),
            user_id=actor.subject_id,
            author_name=payload.author_name,
            bio=payload.bio,
            avatar_url=payload.avatar_url,
            status="SUSPENDED",
            approved_at=None,
            created_at=now,
            updated_at=now,
        )
        row = await self._repository.create_application(
            id=new_id(),
            user_id=actor.subject_id,
            application_reason=payload.application_reason,
            status="PENDING",
            reviewer_id=None,
            review_reason=None,
            applied_at=now,
            reviewed_at=None,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_AUTHOR_APPLY",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_author_application",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_application(row)

    async def list_applications(
        self, *, status: str | None = None, page: PageParams
    ) -> Page[AuthorApplicationResponse]:
        rows, total = await self._repository.list_applications(
            status=status, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_application(row) for row in rows], total=total, params=page
        )

    async def review_application(
        self, actor: Principal, application_id: int, payload: AuthorApplicationReviewRequest
    ) -> AuthorApplicationResponse:
        if payload.decision not in ("APPROVED", "REJECTED"):
            raise ValidationError("decision must be APPROVED or REJECTED")
        row = await self._repository.get_application(application_id)
        if row is None:
            raise NotFoundError("application not found")
        now = datetime.datetime.now(datetime.UTC)
        if payload.decision == "APPROVED":
            await self._approve_author(row, actor.subject_id, now)
        else:
            await self._repository.update_application(
                row,
                status="REJECTED",
                reviewer_id=actor.subject_id,
                review_reason=payload.review_reason,
                reviewed_at=now,
            )
        await self._audit.record(
            self._session,
            action="BLOG_AUTHOR_REVIEW",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_author_application",
            resource_id=int(row.id),
            after_data={
                "decision": payload.decision,
                "review_reason": payload.review_reason,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_AUTHOR_REVIEW",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_author_application",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_application(row)

    async def _approve_author(
        self,
        application: BlogAuthorApplication,
        reviewer_id: int,
        now: datetime.datetime,
    ) -> None:
        author = await self._repository.get_by_user_id(int(application.user_id))
        if author is None:
            author = await self._repository.create_author(
                id=new_id(),
                user_id=int(application.user_id),
                author_name="",
                bio=None,
                avatar_url=None,
                status="ACTIVE",
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        else:
            await self._repository.update_author(
                author, status="ACTIVE", approved_at=now, updated_at=now
            )
        await self._repository.update_application(
            application,
            status="APPROVED",
            reviewer_id=reviewer_id,
            review_reason=None,
            reviewed_at=now,
        )

    def _to_author(self, row: BlogAuthor) -> AuthorResponse:
        return AuthorResponse(
            id=str(int(row.id)),
            user_id=str(int(row.user_id)),
            author_name=str(row.author_name),
            bio=row.bio,
            avatar_url=row.avatar_url,
            status=str(row.status),
            approved_at=row.approved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_application(
        self, row: BlogAuthorApplication
    ) -> AuthorApplicationResponse:
        return AuthorApplicationResponse(
            id=str(int(row.id)),
            user_id=str(int(row.user_id)),
            application_reason=row.application_reason,
            status=str(row.status),
            review_reason=row.review_reason,
            applied_at=row.applied_at,
            reviewed_at=row.reviewed_at,
        )
