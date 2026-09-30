"""app.blog.authors — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class AuthorApplyRequest(ApiModel):
    """Apply to become a blog author."""

    author_name: str
    bio: str | None = None
    avatar_url: str | None = None
    application_reason: str | None = None


class AuthorApplicationReviewRequest(ApiModel):
    """Admin decision for an author application."""

    decision: str  # APPROVED | REJECTED
    review_reason: str | None = None


class AuthorResponse(ApiModel):
    """A blog author."""

    id: StringId
    user_id: StringId
    author_name: str
    bio: str | None = None
    avatar_url: str | None = None
    status: str
    approved_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AuthorApplicationResponse(ApiModel):
    """A blog author application."""

    id: StringId
    user_id: StringId
    application_reason: str | None = None
    status: str
    review_reason: str | None = None
    applied_at: datetime.datetime
    reviewed_at: datetime.datetime | None = None
