"""Live readiness tests.

These tests require a real PostgreSQL and Redis instance described by the
developer's ``.env``. They are skipped when the connection fields
(DB_HOST/DB_NAME/DB_USER, REDIS_HOST) are not filled in, so the suite never
fakes a connection.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_ready_reports_postgres_and_redis_ok(
    live_settings: Settings, live_infrastructure: None
) -> None:
    with TestClient(create_app(live_settings)) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ready"
    assert body["data"]["checks"]["postgres"]["status"] == "ok"
    assert body["data"]["checks"]["redis"]["status"] == "ok"


def test_database_session_dependency_can_be_opened(
    live_settings: Settings, live_infrastructure: None
) -> None:
    with TestClient(create_app(live_settings)) as client:
        engine = client.app.state.engine  # type: ignore[attr-defined]
        assert engine is not None
        factory = client.app.state.session_factory  # type: ignore[attr-defined]
        assert factory is not None
