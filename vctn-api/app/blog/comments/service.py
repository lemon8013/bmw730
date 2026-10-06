"""app.blog.comments — business logic.

Comments are posted by platform users and only become visible after an admin
approves them. The service owns the transaction and the approval policy.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.articles.repository import ArticleRepository
from app.blog.comments.model import BlogComment
from app.blog.comments.repository import CommentRepository
from app.blog.comments.schema import (
    CommentCreateRequest,
    CommentResponse,
    CommentReviewRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class CommentService:
    """Comment management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = CommentRepository(session)
        self._articles = ArticleRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_comments(
        self, article_id: int, *, page: PageParams
    ) -> Page[CommentResponse]:
        rows, total = await self._repository.list_approved(
            article_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def list_pending(self, *, page: PageParams) -> Page[CommentResponse]:
        rows, total = await self._repository.list_pending(
            limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def create_comment(
        self, actor: Principal, article_id: int, payload: CommentCreateRequest
    ) -> CommentResponse:
        article = await self._articles.get_published(article_id)
        if article is None:
            raise NotFoundError("article not found")
        parent_id = int(payload.parent_id) if payload.parent_id else None
        if parent_id is not None:
            parent = await self._repository.get_any(parent_id)
            if parent is None or int(parent.article_id or 0) != article_id:
                raise BusinessRuleError("the parent comment does not belong to this article")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            article_id=article_id,
            user_id=actor.subject_id,
            parent_id=parent_id,
            content=payload.content,
            status="PENDING",
            created_at=now,
            updated_at=now,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_COMMENT_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_comment",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_comment(self, actor: Principal, comment_id: int) -> None:
        row = await self._repository.get_any(comment_id)
        if row is None:
            raise NotFoundError("comment not found")
        is_author = actor.subject_type != "admin" and int(row.user_id or 0) == actor.subject_id
        if actor.subject_type != "admin" and not is_author:
            raise BusinessRuleError("you can only delete your own comments")
        if row.status == "APPROVED" and row.article_id is not None:
            await self._articles.adjust_count(int(row.article_id), "comment_count", -1)
        await self._repository.soft_delete(row)
        await write_operation_log(
            self._session,
            operation="BLOG_COMMENT_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_comment",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def review_comment(
        self, actor: Principal, comment_id: int, payload: CommentReviewRequest
    ) -> CommentResponse:
        if payload.decision not in ("APPROVED", "REJECTED"):
            raise ValidationError("decision must be APPROVED or REJECTED")
        row = await self._repository.get_any(comment_id)
        if row is None:
            raise NotFoundError("comment not found")
        await self._repository.update_status(
            row, status=payload.decision, reviewer_id=actor.subject_id
        )
        if payload.decision == "APPROVED" and row.article_id is not None:
            await self._articles.adjust_count(int(row.article_id), "comment_count", 1)
        await self._audit.record(
            self._session,
            action="BLOG_COMMENT_REVIEW",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_comment",
            resource_id=int(row.id),
            after_data={
                "decision": payload.decision,
                "review_comment": payload.review_comment,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_COMMENT_REVIEW",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_comment",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    def _to_response(self, row: BlogComment) -> CommentResponse:
        return CommentResponse(
            id=str(int(row.id)),
            article_id=None if row.article_id is None else str(int(row.article_id)),
            user_id=None if row.user_id is None else str(int(row.user_id)),
            parent_id=None if row.parent_id is None else str(int(row.parent_id)),
            content=str(row.content),
            status=str(row.status),
            reviewer_id=None if row.reviewer_id is None else str(int(row.reviewer_id)),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
