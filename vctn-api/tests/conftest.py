"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """A TestClient bound to a freshly created application."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def live_infrastructure() -> None:
    """Skip tests that need a real PostgreSQL and Redis instance."""
    settings = get_settings()
    if not (settings.is_database_configured and settings.is_redis_configured):
        pytest.skip("DATABASE_URL / REDIS_URL are not configured; live check skipped")
