"""CORS behaviour is driven by configuration and never by a wildcard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_configured_origin_is_allowed() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:5173")
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "X-Trace-ID" in response.headers


def test_unlisted_origin_is_rejected() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:5173")
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400


def test_wildcard_origin_is_rejected_by_configuration() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        create_app(Settings(CORS_ORIGINS="*"))
