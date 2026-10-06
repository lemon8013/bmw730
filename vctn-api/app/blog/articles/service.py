"""app.blog.articles — business logic.

Articles mix three audiences:

* the public reader (anonymous or platform) who only sees published articles,
* the platform author who drafts, edits and publishes their own articles,
* the admin reviewer who approves or rejects submissions.

The service is the transaction boundary and the only place that decides policy.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.articles.model import BlogArticle
from app.blog.articles.repository import ArticleRepository
from app.blog.articles.schema import (
    ArticleCreateRequest,
    ArticleResponse,
    ArticleReviewRequest,
    ArticleUpdateRequest,
)
from app.blog.authors.repository import AuthorRepository
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


def _render_markdown(markdown_text: str | None) -> str | None:
    """Render Markdown to sanitized HTML (no raw user input is stored unsafe)."""
    if not markdown_text:
        return None
    import bleach
    from markdown_it import MarkdownIt

    html = MarkdownIt("commonmark").enable("table").render(markdown_text)
    allowed = {
        "p", "br", "strong", "em", "code", "pre", "ul", "ol", "li", "a", "h1",
        "h2", "h3", "h4", "h5", "h6", "blockquote", "table", "thead", "tbody",
        "tr", "th", "td", "hr", "img",
    }
    attrs = {"a": ["href", "title"], "img": ["src", "alt"]}
    return bleach.clean(html, tags=allowed, attributes=attrs, strip=True)


class ArticleService:
    """Article management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ArticleRepository(session)
        self._authors = AuthorRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def list_articles(
        self,
        *,
        keyword: str | None = None,
        category_id: int | None = None,
        author_id: int | None = None,
        status: str | None = None,
        page: PageParams,
        actor: Principal | None = None,
    ) -> Page[ArticleResponse]:
        """List articles.

        Anything other than ``PUBLISHED`` is private to its author: the caller
        must be a signed-in platform user and the result is narrowed to their
        own author row. Without that guard ``?status=DRAFT`` would hand every
        author's unpublished work to an anonymous caller.
        """
        resolved_author_id = author_id
        resolved_status = status or "PUBLISHED"
        if resolved_status != "PUBLISHED":
            if actor is None or not actor.is_platform_user:
                raise AuthenticationError("sign in to list unpublished articles")
            own = await self._authors.get_by_user_id(actor.subject_id)
            if own is None:
                return Page.build(items=[], total=0, params=page)
            resolved_author_id = int(own.id)
        rows, total = await self._repository.list_published(
            keyword=keyword,
            category_id=category_id,
            author_id=resolved_author_id,
            status=resolved_status,
            limit=page.limit,
            offset=page.offset,
        )
        items = []
        for row in rows:
            items.append(await self._to_response(row))
        return Page.build(items=items, total=total, params=page)

    async def list_pending(
        self, *, page: PageParams
    ) -> Page[ArticleResponse]:
        rows, total = await self._repository.list_pending(
            limit=page.limit, offset=page.offset
        )
        items = [await self._to_response(row) for row in rows]
        return Page.build(items=items, total=total, params=page)

    async def get_article(self, article_id: int) -> ArticleResponse:
        """Public detail: only published articles are visible; counts one view."""
        row = await self._repository.get_published(article_id)
        if row is None:
            raise NotFoundError("article not found")
        await self._repository.increment_view(row)
        await self._session.commit()
        return await self._to_response(row)

    async def get_article_for_edit(self, actor: Principal, article_id: int) -> ArticleResponse:
        row = await self._repository.get_any(article_id)
        if row is None:
            raise NotFoundError("article not found")
        await self._assert_owner(actor, row)
        return await self._to_response(row)

    async def get_tags(self, article_id: int) -> list[str]:
        row = await self._repository.get_published(article_id)
        if row is None:
            raise NotFoundError("article not found")
        return await self._repository.list_tags(int(row.id))

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    async def create_article(
        self, actor: Principal, payload: ArticleCreateRequest
    ) -> ArticleResponse:
        author = await self._authors.get_by_user_id(actor.subject_id)
        if author is None:
            raise BusinessRuleError("you must apply to become an author first")
        if await self._repository.get_by_slug(payload.slug):
            raise ConflictError("slug is already taken")
        now = datetime.datetime.now(datetime.UTC)
        category_id = int(payload.category_id) if payload.category_id else None
        row = await self._repository.create(
            id=new_id(),
            author_id=int(author.id),
            category_id=category_id,
            title=payload.title,
            slug=payload.slug,
            summary=payload.summary,
            cover_url=payload.cover_url,
            content_markdown=payload.content_markdown,
            content_html=_render_markdown(payload.content_markdown),
            status="DRAFT",
            review_status="NOT_REQUIRED",
            published_at=None,
            view_count=0,
            like_count=0,
            favorite_count=0,
            comment_count=0,
            created_at=now,
            updated_at=now,
        )
        await self._repository.set_tags(int(row.id), payload.tags)
        await write_operation_log(
            self._session,
            operation="BLOG_ARTICLE_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_article",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row)

    async def update_article(
        self, actor: Principal, article_id: int, payload: ArticleUpdateRequest
    ) -> ArticleResponse:
        row = await self._repository.get_any(article_id)
        if row is None:
            raise NotFoundError("article not found")
        await self._assert_owner(actor, row)
        if payload.slug and payload.slug != row.slug:
            existing = await self._repository.get_by_slug(payload.slug)
            if existing is not None and int(existing.id) != int(row.id):
                raise ConflictError("slug is already taken")

        changes: dict[str, object] = {}
        for field in ("title", "summary", "cover_url"):
            value = getattr(payload, field)
            if value is not None:
                changes[field] = value
        if payload.slug is not None:
            changes["slug"] = payload.slug
        if payload.category_id is not None:
            changes["category_id"] = (
                int(payload.category_id) if payload.category_id else None
            )
        if payload.content_markdown is not None:
            changes["content_markdown"] = payload.content_markdown
            changes["content_html"] = _render_markdown(payload.content_markdown)
        if changes:
            await self._repository.update(row, **changes)
            row.updated_at = datetime.datetime.now(datetime.UTC)
            await self._session.flush()
        if payload.tags is not None:
            await self._repository.set_tags(int(row.id), payload.tags)
        await write_operation_log(
            self._session,
            operation="BLOG_ARTICLE_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_article",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row)

    async def delete_article(self, actor: Principal, article_id: int) -> None:
        row = await self._repository.get_any(article_id)
        if row is None:
            raise NotFoundError("article not found")
        if actor.subject_type != "admin":
            await self._assert_owner(actor, row)
        await self._repository.soft_delete(row)
        await write_operation_log(
            self._session,
            operation="BLOG_ARTICLE_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_article",
            resource_id=int(row.id),
        )
        await self._session.commit()

    async def publish_article(self, actor: Principal, article_id: int) -> ArticleResponse:
        row = await self._repository.get_any(article_id)
        if row is None:
            raise NotFoundError("article not found")
        await self._assert_owner(actor, row)
        if row.status == "PUBLISHED":
            raise BusinessRuleError("article is already published")
        row.status = "PUBLISHED"
        row.published_at = datetime.datetime.now(datetime.UTC)
        if row.review_status == "NOT_REQUIRED":
            row.review_status = "PENDING"
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await write_operation_log(
            self._session,
            operation="BLOG_ARTICLE_PUBLISH",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_article",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row)

    async def review_article(
        self, actor: Principal, article_id: int, payload: ArticleReviewRequest
    ) -> ArticleResponse:
        if payload.decision not in ("APPROVED", "REJECTED"):
            raise ValidationError("decision must be APPROVED or REJECTED")
        row = await self._repository.get_any(article_id)
        if row is None:
            raise NotFoundError("article not found")
        now = datetime.datetime.now(datetime.UTC)
        row.review_status = payload.decision
        row.reviewer_id = actor.subject_id
        row.reviewed_at = now
        if payload.decision == "REJECTED":
            row.status = "OFFLINE"
        row.updated_at = now
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="BLOG_ARTICLE_REVIEW",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_article",
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
            operation="BLOG_ARTICLE_REVIEW",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_article",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return await self._to_response(row)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _assert_owner(self, actor: Principal, row: BlogArticle) -> None:
        if actor.subject_type == "admin":
            return
        author = await self._authors.get_by_user_id(actor.subject_id)
        if author is None or int(author.id) != int(row.author_id):
            raise BusinessRuleError("you are not the author of this article")

    async def _to_response(self, row: BlogArticle) -> ArticleResponse:
        return ArticleResponse(
            id=str(int(row.id)),
            author_id=str(int(row.author_id)),
            category_id=None if row.category_id is None else str(int(row.category_id)),
            title=str(row.title),
            slug=str(row.slug),
            summary=row.summary,
            cover_url=row.cover_url,
            content_markdown=row.content_markdown,
            content_html=row.content_html,
            status=str(row.status),
            review_status=str(row.review_status),
            reviewer_id=None if row.reviewer_id is None else str(int(row.reviewer_id)),
            reviewed_at=row.reviewed_at,
            published_at=row.published_at,
            view_count=int(row.view_count or 0),
            like_count=int(row.like_count or 0),
            favorite_count=int(row.favorite_count or 0),
            comment_count=int(row.comment_count or 0),
            tags=await self._repository.list_tags(int(row.id)),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
