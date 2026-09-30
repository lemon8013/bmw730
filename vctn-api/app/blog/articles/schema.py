"""app.blog.articles — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class ArticleCreateRequest(ApiModel):
    """Create a draft article."""

    title: str
    slug: str
    summary: str | None = None
    cover_url: str | None = None
    category_id: OptionalStringId = None
    content_markdown: str | None = None
    tags: list[str] = []


class ArticleUpdateRequest(ApiModel):
    """Update a draft article."""

    title: str | None = None
    slug: str | None = None
    summary: str | None = None
    cover_url: str | None = None
    category_id: OptionalStringId = None
    content_markdown: str | None = None
    tags: list[str] | None = None


class ArticleReviewRequest(ApiModel):
    """Admin review decision for an article."""

    decision: str  # APPROVED | REJECTED
    review_comment: str | None = None


class ArticleResponse(ApiModel):
    """A blog article."""

    id: StringId
    author_id: StringId
    category_id: OptionalStringId = None
    title: str
    slug: str
    summary: str | None = None
    cover_url: str | None = None
    content_markdown: str | None = None
    content_html: str | None = None
    status: str
    review_status: str
    reviewer_id: OptionalStringId = None
    reviewed_at: datetime.datetime | None = None
    published_at: datetime.datetime | None = None
    view_count: int
    like_count: int
    favorite_count: int
    comment_count: int
    tags: list[str] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ArticleTagResponse(ApiModel):
    """A single tag name."""

    tag_name: str
