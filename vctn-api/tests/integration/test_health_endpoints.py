"""Integration tests for the system endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


def test_version_returns_application_metadata(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["app_name"] == "vctn-api"
    assert data["version"]
    assert data["environment"]


def test_ready_is_executable_and_reports_every_check(client: TestClient) -> None:
    response = client.get("/ready")
    # Without configured infrastructure the probe reports 503, which is a valid
    # execution of the endpoint; the payload must always carry both checks.
    assert response.status_code in (200, 503)
    checks = response.json()["data"]["checks"]
    assert set(checks) == {"postgres", "redis"}
    for check in checks.values():
        assert check["status"] in {"ok", "error", "not_configured"}


def test_openapi_document_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "vctn-api"


def test_unknown_path_returns_the_unified_envelope(client: TestClient) -> None:
    response = client.get("/definitely-not-a-route")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 404001
    assert body["data"] is None
