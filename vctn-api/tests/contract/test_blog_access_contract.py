"""Contract test for blog route ordering.

``GET /blog/authors/applications`` used to be declared *after*
``GET /blog/authors/{author_id}``. FastAPI matches in registration order, so
``applications`` was parsed as an author id and ``int("applications")`` raised a
500 instead of answering with an auth error.

The same trap applies to ``/articles/review-queue`` and ``/comments/pending``.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

# Every literal segment that shares a prefix with a parameterised route.
_LITERAL_BEFORE_PARAM = (
    ("/api/v1/blog/authors", "/api/v1/blog/authors/{author_id}"),
    ("/api/v1/blog/articles", "/api/v1/blog/articles/{article_id}"),
    ("/api/v1/blog/authors/applications", "/api/v1/blog/authors/{author_id}"),
    ("/api/v1/blog/articles/review-queue", "/api/v1/blog/articles/{article_id}"),
    ("/api/v1/blog/comments/pending", "/api/v1/blog/comments/{comment_id}"),
)


def test_literal_segments_are_declared_before_parameterised_ones(
    client: TestClient,
) -> None:
    paths = list(client.get("/openapi.json").json()["paths"])
    for literal, parameterised in _LITERAL_BEFORE_PARAM:
        if literal not in paths or parameterised not in paths:
            continue
        assert paths.index(literal) < paths.index(parameterised), (
            f"{literal} must be registered before {parameterised}"
        )


def test_author_applications_does_not_500(client: TestClient) -> None:
    """A 500 here means the literal route was swallowed by ``{author_id}``."""
    response = client.get("/api/v1/blog/authors/applications")
    payload: dict[str, Any] = response.json()
    assert response.status_code != 500
    assert payload["code"] != 500000
