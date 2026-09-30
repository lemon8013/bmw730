"""Guards for the "one config file, no hard coded configuration" rule.

These tests fail if a new tunable is added to :class:`Settings` without being
documented on the single configuration surface (``.env.example``), or if a
configured value stops reaching the component that consumes it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import Settings
from app.shared.database.engine import build_engine
from app.shared.redis.client import build_redis

_ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def _declared_fields() -> set[str]:
    return {name for name in Settings.model_fields if not name.startswith("_")}


def test_env_example_exists() -> None:
    assert _ENV_EXAMPLE.is_file()


def test_every_setting_is_documented_in_env_example() -> None:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip()
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    undocumented = sorted(_declared_fields() - documented)
    assert undocumented == [], f"undocumented settings: {undocumented}"


def test_env_example_has_no_unknown_keys() -> None:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip()
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    unknown = sorted(documented - _declared_fields())
    assert unknown == [], f"unknown keys in .env.example: {unknown}"


def test_env_example_never_ships_secrets() -> None:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    secret_keys = {
        "DATABASE_URL",
        "REDIS_URL",
        "DB_HOST",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "REDIS_HOST",
        "REDIS_USERNAME",
        "REDIS_PASSWORD",
    }
    for line in text.splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in secret_keys:
            assert value == "", f"{key} must stay empty in .env.example"


def test_database_connection_comes_from_fields_not_a_url() -> None:
    settings = Settings(
        DB_HOST="db.internal",
        DB_PORT=5432,
        DB_NAME="vctn",
        DB_USER="vctn_app",
        DB_PASSWORD="secret",
    )
    assert settings.database_url == ("postgresql+asyncpg://vctn_app:secret@db.internal:5432/vctn")


def test_engine_uses_the_assembled_database_url() -> None:
    settings = Settings(
        DB_HOST="db.internal",
        DB_PORT=5544,
        DB_NAME="vctn",
        DB_USER="vctn_app",
        DB_PASSWORD="secret",
    )
    engine = build_engine(settings)
    try:
        url = engine.url
        assert url.host == "db.internal"
        assert url.port == 5544
        assert url.database == "vctn"
        assert url.username == "vctn_app"
        assert url.password == "secret"
        assert url.drivername == "postgresql+asyncpg"
    finally:
        asyncio.run(engine.dispose())


def test_redis_client_uses_the_assembled_url() -> None:
    settings = Settings(REDIS_HOST="cache.internal", REDIS_PORT=6380, REDIS_DB=3)
    client = build_redis(settings)
    try:
        pool = client.connection_pool
        kwargs = pool.connection_kwargs
        assert kwargs["host"] == "cache.internal"
        assert kwargs["port"] == 6380
        assert kwargs["db"] == 3
    finally:
        asyncio.run(client.aclose())


def test_engine_refuses_an_unconfigured_database() -> None:
    try:
        build_engine(Settings())
    except ValueError as exc:
        assert "PostgreSQL is not configured" in str(exc)
    else:  # pragma: no cover - the engine must refuse an unconfigured connection
        raise AssertionError("build_engine accepted an unconfigured connection")


def test_redis_client_refuses_an_unconfigured_connection() -> None:
    try:
        build_redis(Settings())
    except ValueError as exc:
        assert "Redis is not configured" in str(exc)
    else:  # pragma: no cover - the client must refuse an unconfigured connection
        raise AssertionError("build_redis accepted an unconfigured connection")
