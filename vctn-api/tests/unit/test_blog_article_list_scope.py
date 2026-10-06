"""Unit tests for the article list visibility rule.

``GET /blog/articles`` is anonymous by dependency, so a caller could ask for
``status=DRAFT`` and read every author's unpublished work. The service must
refuse anonymous callers for any non-published status and narrow the result to
the caller's own author row.

These tests stub the repositories so they stay free of live infrastructure.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.blog.articles.service import ArticleService
from app.core.exceptions import AuthenticationError
from app.shared.auth.context import Principal
from app.shared.pagination.params import PageParams


class _StubAuthors:
    def __init__(self, author_id: int | None) -> None:
        self._author_id = author_id

    async def get_by_user_id(self, user_id: int) -> Any | None:
        if self._author_id is None:
            return None
        return type("Row", (), {"id": self._author_id})()


class _StubArticles:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def list_published(self, **kwargs: Any) -> tuple[list[Any], int]:
        self.calls.append(kwargs)
        return [], 0


def _service(author_id: int | None) -> tuple[ArticleService, _StubArticles]:
    service = ArticleService.__new__(ArticleService)
    stub = _StubArticles()
    service._repository = stub  # type: ignore[attr-defined]
    service._authors = _StubAuthors(author_id)  # type: ignore[attr-defined]
    return service, stub


def _platform() -> Principal:
    return Principal(
        subject_id=901,
        subject_type="platform",
        session_id=1,
        username="reader",
        display_name="reader",
    )


@pytest.mark.asyncio()
async def test_anonymous_caller_cannot_list_drafts() -> None:
    service, _ = _service(author_id=None)
    with pytest.raises(AuthenticationError):
        await service.list_articles(status="DRAFT", page=PageParams(page=1, page_size=20))


@pytest.mark.asyncio()
async def test_anonymous_caller_can_list_published() -> None:
    service, stub = _service(author_id=None)
    await service.list_articles(page=PageParams(page=1, page_size=20))
    assert stub.calls[0]["status"] == "PUBLISHED"
    assert stub.calls[0]["author_id"] is None


@pytest.mark.asyncio()
async def test_drafts_are_narrowed_to_the_callers_own_author_row() -> None:
    service, stub = _service(author_id=4242)
    await service.list_articles(
        status="DRAFT", page=PageParams(page=1, page_size=20), actor=_platform()
    )
    assert stub.calls[0]["status"] == "DRAFT"
    assert stub.calls[0]["author_id"] == 4242


@pytest.mark.asyncio()
async def test_a_platform_user_without_an_author_row_sees_nothing() -> None:
    service, stub = _service(author_id=None)
    page = await service.list_articles(
        status="DRAFT", page=PageParams(page=1, page_size=20), actor=_platform()
    )
    assert page.total == 0
    assert stub.calls == []
