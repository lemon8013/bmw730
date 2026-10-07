"""The seed command must not be able to put test accounts into production.

Test mode creates logins whose passwords come from an environment variable and
are therefore known to everyone with access to CI. One careless run against
production leaves a working account on the internet, which no amount of
after-the-fact cleanup makes safe - the credentials were already published.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.scripts.seed import cli


@pytest.fixture()
def _production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli, "get_settings", lambda: Settings(_env_file=None, APP_ENV="production")
    )


def test_test_mode_is_refused_in_production(
    _production: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = False

    def _must_not_run(**_kwargs: object) -> None:  # pragma: no cover - guard
        nonlocal called
        called = True
        raise AssertionError("the seed must not execute in production test mode")

    monkeypatch.setattr(cli, "execute", _must_not_run)

    exit_code = cli.main(["--mode=test"])

    assert exit_code == cli._EXIT_PRECONDITION
    assert called is False


def test_system_mode_is_still_allowed_in_production(
    _production: None, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Refusing test mode must not block the catalogue seed, which is required."""
    seen: dict[str, object] = {}

    class _Outcome:
        status = "PASS"

    async def _fake_execute(**kwargs: object) -> _Outcome:
        seen.update(kwargs)
        return _Outcome()

    monkeypatch.setattr(cli, "execute", _fake_execute)
    monkeypatch.setattr(cli, "render_final_block", lambda *_a, **_k: "")
    monkeypatch.setattr(cli, "render_markdown", lambda *_a, **_k: "")

    exit_code = cli.main(["--mode=system", "--no-report"])

    assert exit_code == cli._EXIT_OK
    assert seen["mode"] == "system"


def test_test_mode_is_allowed_outside_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli, "get_settings", lambda: Settings(_env_file=None, APP_ENV="development")
    )

    class _Outcome:
        status = "PASS"

    async def _fake_execute(**_kwargs: object) -> _Outcome:
        return _Outcome()

    monkeypatch.setattr(cli, "execute", _fake_execute)
    monkeypatch.setattr(cli, "render_final_block", lambda *_a, **_k: "")
    monkeypatch.setattr(cli, "render_markdown", lambda *_a, **_k: "")

    assert cli.main(["--mode=test", "--no-report"]) == cli._EXIT_OK
