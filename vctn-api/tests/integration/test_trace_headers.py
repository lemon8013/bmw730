"""Integration tests for trace id / request id propagation."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_identifiers_are_generated_when_absent(client: TestClient) -> None:
    response = client.get("/health")
    assert len(response.headers["X-Trace-ID"]) == 32
    assert len(response.headers["X-Request-ID"]) == 32
    assert response.headers["X-Trace-ID"] != response.headers["X-Request-ID"]


def test_client_supplied_identifiers_are_propagated(client: TestClient) -> None:
    response = client.get(
        "/health",
        headers={"X-Trace-ID": "trace-abc-123", "X-Request-ID": "request-abc-123"},
    )
    assert response.headers["X-Trace-ID"] == "trace-abc-123"
    assert response.headers["X-Request-ID"] == "request-abc-123"


def test_unsafe_identifier_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Trace-ID": "ab(c)"})
    assert response.headers["X-Trace-ID"] != "ab(c)"
    assert len(response.headers["X-Trace-ID"]) == 32
