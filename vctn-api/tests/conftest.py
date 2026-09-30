"""Shared pytest fixtures.

The suite must never depend on the developer's local ``.env``: a real database
or Redis endpoint in that file would make results machine dependent. Setting
``VCTN_ENV_FILE`` to a blank value disables dotenv loading before any
application module is imported.

Tests that genuinely need live infrastructure opt back in through the real
``.env`` via the ``live_settings`` fixture.
"""

from __future__ import annotations

import os

# Must happen before `app.core.config` is imported: the dotenv file is resolved
# when the Settings class is defined.
os.environ["VCTN_ENV_FILE"] = ""

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """A TestClient bound to a freshly created, hermetically configured app."""
    with TestClient(create_app(Settings(_env_file=None))) as test_client:
        yield test_client


@pytest.fixture()
def live_settings() -> Settings:
    """Settings loaded from the real local ``.env``; for live tests only."""
    return Settings(_env_file=".env")


@pytest.fixture()
def live_infrastructure(live_settings: Settings) -> None:
    """Skip tests that need a real PostgreSQL and Redis instance."""
    if not (live_settings.is_database_configured and live_settings.is_redis_configured):
        missing = live_settings.missing_database_fields
        detail = f"; missing: {', '.join(missing)}" if missing else ""
        pytest.skip(
            f"PostgreSQL / Redis connection is not configured in .env; live check skipped{detail}"
        )
