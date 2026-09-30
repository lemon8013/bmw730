"""Contract tests: every endpoint answers with the unified envelope."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _assert_envelope(payload: dict[str, Any]) -> None:
    assert set(payload) == {"code", "message", "data"}
    assert isinstance(payload["code"], int)
    assert isinstance(payload["message"], str)


def test_success_envelope_contract(client: TestClient) -> None:
    for path in ("/health", "/version"):
        payload = client.get(path).json()
        _assert_envelope(payload)
        assert payload["code"] == 0
        assert payload["message"] == "success"


def test_error_envelope_contract(client: TestClient) -> None:
    payload = client.get("/definitely-not-a-route").json()
    _assert_envelope(payload)
    assert payload["code"] != 0
    assert payload["data"] is None


def test_ready_envelope_contract(client: TestClient) -> None:
    payload = client.get("/ready").json()
    _assert_envelope(payload)
    assert isinstance(payload["data"], dict)
    assert "checks" in payload["data"]
