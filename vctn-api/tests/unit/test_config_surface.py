"""Guards for the "one config file, no hard coded configuration" rule.

These tests fail if a new tunable is added to :class:`Settings` without being
documented on the single configuration surface (``.env.example``), or if a
configured value stops reaching the component that consumes it.
"""

from __future__ import annotations

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
    for line in text.splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in {"DATABASE_URL", "REDIS_URL"}:
            assert value == "", f"{key} must stay empty in .env.example"


def test_database_url_is_required_by_the_engine() -> None:
    settings = Settings(DATABASE_URL="")
    try:
        build_engine(settings)
    except ValueError as exc:
        assert "DATABASE_URL" in str(exc)
    else:  # pragma: no cover - the engine must refuse an unconfigured URL
        raise AssertionError("build_engine accepted an empty DATABASE_URL")


def test_redis_url_is_required_by_the_client() -> None:
    settings = Settings(REDIS_URL="")
    try:
        build_redis(settings)
    except ValueError as exc:
        assert "REDIS_URL" in str(exc)
    else:  # pragma: no cover - the client must refuse an unconfigured URL
        raise AssertionError("build_redis accepted an empty REDIS_URL")
