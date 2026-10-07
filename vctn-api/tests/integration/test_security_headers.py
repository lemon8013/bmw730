"""Browser security headers, Host allow-listing and documentation exposure.

Every assertion here is about what leaves the process on the wire, which is
what an enterprise security review actually checks.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

#: ``TestClient`` always sends this Host unless told otherwise.
TEST_HOST = "testserver"


def _production(**overrides: object) -> Settings:
    """A settings object that survives ``validate_startup`` in production."""
    base: dict[str, object] = {
        "_env_file": None,
        "APP_ENV": "production",
        "AUTH_JWT_SECRET": "s" * 48,
        "ALLOWED_HOSTS": TEST_HOST,
        "CORS_ORIGINS": "https://ops.example.com",
        "CORS_ALLOW_METHODS": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "CORS_ALLOW_HEADERS": "Authorization,Content-Type",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_the_baseline_headers_are_always_present() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "microphone=()" in response.headers["permissions-policy"]


def test_hsts_is_absent_until_it_is_switched_on() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert "strict-transport-security" not in client.get("/health").headers

    settings = Settings(
        _env_file=None,
        SECURITY_HSTS_ENABLED=True,
        SECURITY_HSTS_MAX_AGE_SECONDS=600,
        SECURITY_HSTS_INCLUDE_SUBDOMAINS=False,
    )
    with TestClient(create_app(settings)) as client:
        value = client.get("/health").headers["strict-transport-security"]

    assert value == "max-age=600"


def test_hsts_carries_include_subdomains_when_asked() -> None:
    settings = Settings(_env_file=None, SECURITY_HSTS_ENABLED=True)
    with TestClient(create_app(settings)) as client:
        value = client.get("/health").headers["strict-transport-security"]

    assert "includeSubDomains" in value


def test_a_blank_csp_omits_the_header_rather_than_becoming_permissive() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        headers = client.get("/health").headers

    assert "content-security-policy" not in headers
    assert "content-security-policy-report-only" not in headers


def test_a_configured_csp_is_enforced_unless_report_only() -> None:
    settings = Settings(_env_file=None, SECURITY_CSP="default-src 'self'")
    with TestClient(create_app(settings)) as client:
        enforced = client.get("/health").headers

    assert enforced["content-security-policy"] == "default-src 'self'"
    assert "content-security-policy-report-only" not in enforced

    report_only = Settings(
        _env_file=None,
        SECURITY_CSP="default-src 'self'",
        SECURITY_CSP_REPORT_ONLY=True,
    )
    with TestClient(create_app(report_only)) as client:
        observed = client.get("/health").headers

    assert observed["content-security-policy-report-only"] == "default-src 'self'"
    assert "content-security-policy" not in observed


def test_documentation_is_served_outside_production() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_production_does_not_publish_the_endpoint_catalogue() -> None:
    with TestClient(create_app(_production())) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_documentation_can_be_forced_back_on_when_an_operator_asks() -> None:
    with TestClient(create_app(_production(DOCS_ENABLED=True))) as client:
        assert client.get("/docs").status_code == 200


def test_an_unlisted_host_is_rejected() -> None:
    settings = Settings(_env_file=None, ALLOWED_HOSTS="ops.example.com")
    with TestClient(create_app(settings)) as client:
        response = client.get("/docs")

    assert response.status_code == 400
    assert response.json()["message"] == "invalid host header"
    # The rejection still carries its trace id, otherwise it is untraceable.
    assert "X-Trace-ID" in response.headers


def test_the_listed_host_is_accepted_with_or_without_a_port() -> None:
    settings = Settings(_env_file=None, ALLOWED_HOSTS="ops.example.com")
    with TestClient(create_app(settings), base_url="https://ops.example.com") as client:
        assert client.get("/docs").status_code == 200


def test_probes_are_exempt_so_health_checks_never_depend_on_the_host_header() -> None:
    """A container runtime polls with whatever Host it likes; it must work."""
    settings = Settings(_env_file=None, ALLOWED_HOSTS="ops.example.com")
    with TestClient(create_app(settings)) as client:
        for probe in ("/health", "/ready", "/version"):
            assert client.get(probe).status_code in {200, 503}, probe


def test_production_refuses_to_boot_with_debug_enabled() -> None:
    with pytest.raises(ValueError, match="APP_DEBUG"):
        _production(APP_DEBUG=True).validate_startup()


def test_production_requires_a_host_allow_list() -> None:
    with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
        _production(ALLOWED_HOSTS="").validate_startup()


def test_production_requires_an_enumerated_cors_list() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        _production(CORS_ORIGINS="").validate_startup()

    with pytest.raises(ValueError, match="CORS methods and headers"):
        _production(CORS_ALLOW_METHODS="*").validate_startup()
