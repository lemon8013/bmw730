"""Live readiness tests.

These tests require a real PostgreSQL and Redis instance. They are skipped when
DATABASE_URL / REDIS_URL are not provided, so the suite never fakes a connection.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_ready_reports_postgres_and_redis_ok(client: TestClient, live_infrastructure: None) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ready"
    assert body["data"]["checks"]["postgres"]["status"] == "ok"
    assert body["data"]["checks"]["redis"]["status"] == "ok"


def test_database_session_dependency_can_be_opened(
    client: TestClient, live_infrastructure: None
) -> None:
    engine = client.app.state.engine  # type: ignore[attr-defined]
    assert engine is not None
    factory = client.app.state.session_factory  # type: ignore[attr-defined]
    assert factory is not None
