"""Unit tests for the operations reports.

The reports are read-only, so these tests do not need a database: the
repository is stubbed and the assertions are about the arithmetic the service
does *after* the query. That arithmetic is where a report goes wrong in ways
nobody notices:

* a rate divides by a total, and the total is zero on a fresh installation;
* a trend axis built from the rows that exist makes a window look calmer than
  it was, because the quiet days simply never appear;
* a CSV written by hand breaks the moment a value contains a comma.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

import pytest

from app.core.exceptions import ValidationError
from app.ops.reports.schema import DEFAULT_RANKING_LIMIT, MAX_RANKING_LIMIT
from app.ops.reports.service import ReportService, _render_csv


class _StubRepository:
    """Every repository method the reports call, answering from memory."""

    def __init__(
        self,
        *,
        host_status: dict[str, int] | None = None,
        services: tuple[int, int, float] = (0, 0, 0.0),
        alerts: tuple[int, int, int, dict[str, int], float | None] = (0, 0, 0, {}, None),
        availability: tuple[int, int] = (0, 0),
        agents: tuple[int, int] = (0, 0),
        trend: tuple[dict[str, dict[str, int]], dict[str, int]] | None = None,
        ranking: Sequence[tuple[Any, ...]] = (),
        availability_rows: Sequence[tuple[Any, ...]] = (),
    ) -> None:
        self._host_status = host_status or {}
        self._services = services
        self._alerts = alerts
        self._availability = availability
        self._agents = agents
        self._trend = trend or ({}, {})
        self._ranking = list(ranking)
        self._availability_rows = list(availability_rows)

    async def count_hosts_by_status(self) -> dict[str, int]:
        return dict(self._host_status)

    async def aggregate_services(
        self, *, abnormal_statuses: frozenset[str]
    ) -> tuple[int, int, float]:
        return self._services

    async def aggregate_alerts(
        self, *, since: datetime.datetime, active_statuses: frozenset[str]
    ) -> tuple[int, int, int, dict[str, int], float | None]:
        return self._alerts

    async def aggregate_availability(self, *, since: datetime.datetime) -> tuple[int, int]:
        return self._availability

    async def aggregate_agents(self, *, online_status: str) -> tuple[int, int]:
        return self._agents

    async def alert_trend(
        self, *, since: datetime.datetime
    ) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
        return self._trend

    async def alert_ranking(
        self, *, since: datetime.datetime, limit: int
    ) -> list[tuple[Any, ...]]:
        self.last_limit = limit
        return list(self._ranking)

    async def availability_rows(self, *, since: datetime.datetime) -> list[tuple[Any, ...]]:
        return list(self._availability_rows)


def _service(repository: _StubRepository) -> ReportService:
    service = ReportService(session=None)  # type: ignore[arg-type]
    service._repository = repository  # type: ignore[assignment]
    return service


@pytest.mark.asyncio()
async def test_an_empty_installation_yields_zeros_instead_of_an_error() -> None:
    """The first thing an operator opens must render, not raise."""
    summary = await _service(_StubRepository()).summary(days=7)

    assert summary.host.total == 0
    assert summary.host.online_rate == 0.0
    assert summary.service.availability_rate == 0.0
    assert summary.alert.resolve_rate == 0.0
    assert summary.alert.mttr_seconds is None
    assert summary.availability.success_rate == 0.0
    assert summary.agent.online == 0


@pytest.mark.asyncio()
async def test_every_severity_is_present_even_when_only_one_fired() -> None:
    """A caller renders a fixed breakdown, so every key must exist."""
    repository = _StubRepository(alerts=(1, 0, 1, {"ERROR": 1}, None))
    summary = await _service(repository).summary(days=7)

    assert summary.alert.by_severity == {"CRITICAL": 0, "ERROR": 1, "INFO": 0, "WARNING": 0}


@pytest.mark.asyncio()
async def test_rates_are_computed_from_the_fleet_not_hard_coded() -> None:
    repository = _StubRepository(
        host_status={"ONLINE": 3, "OFFLINE": 1},
        alerts=(4, 3, 1, {}, 120.0),
        availability=(10, 1),
    )
    summary = await _service(repository).summary(days=7)

    assert summary.host.online == 3
    assert summary.host.total == 4
    assert summary.host.online_rate == pytest.approx(0.75)
    assert summary.alert.resolve_rate == pytest.approx(0.75)
    assert summary.availability.success_rate == pytest.approx(0.9)
    assert summary.alert.mttr_seconds == pytest.approx(120.0)


@pytest.mark.asyncio()
async def test_the_trend_axis_is_dense_even_when_the_days_are_quiet() -> None:
    """A hole in the axis would read as "nothing happened" by accident."""
    trend = await _service(_StubRepository()).alert_trend(days=7)

    dates = [point.date for point in trend.points]
    assert len(dates) == 8  # the window is inclusive of both ends
    assert dates == sorted(dates)
    parsed = [datetime.date.fromisoformat(day) for day in dates]
    assert parsed[-1] - parsed[0] == datetime.timedelta(days=7)
    assert all(point.fired == 0 for point in trend.points)


@pytest.mark.asyncio()
async def test_a_busy_day_is_counted_on_its_own_date() -> None:
    """Fired and resolved are two columns; merging them in SQL loses days."""
    today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    repository = _StubRepository(
        trend=({today: {"CRITICAL": 2, "WARNING": 1}}, {today: 2})
    )
    trend = await _service(repository).alert_trend(days=1)

    last = trend.points[-1]
    assert last.date == today
    assert last.fired == 3
    assert last.resolved == 2
    assert last.by_severity["CRITICAL"] == 2


@pytest.mark.asyncio()
async def test_the_ranking_reports_the_worst_level_and_a_stable_rank() -> None:
    repository = _StubRepository(
        ranking=[("HOST", 11, "CPU_HIGH", 9, 2, 3, datetime.datetime.now(datetime.UTC))]
    )
    ranking = await _service(repository).alert_ranking(days=7, limit=5)

    assert repository.last_limit == 5
    assert len(ranking.rows) == 1
    assert ranking.rows[0].rank == 1
    assert ranking.rows[0].worst_severity == "ERROR"
    assert ranking.rows[0].resource_id == "11"


@pytest.mark.asyncio()
async def test_an_unmapped_severity_rank_renders_as_absent() -> None:
    """Rank 0 means "no known level", which must not print as INFO."""
    repository = _StubRepository(ranking=[("SERVICE", None, "DOWN", 1, 0, 0, None)])
    ranking = await _service(repository).alert_ranking(days=7)

    assert ranking.rows[0].worst_severity is None
    assert ranking.rows[0].resource_id is None


@pytest.mark.asyncio()
async def test_an_unsupported_report_is_rejected_before_anything_runs() -> None:
    with pytest.raises(ValidationError):
        await _service(_StubRepository()).export(report="does-not-exist", days=7)


@pytest.mark.asyncio()
async def test_the_ranking_limit_falls_back_and_is_capped() -> None:
    repository = _StubRepository()
    service = _service(repository)

    assert service._capped_limit(0) == DEFAULT_RANKING_LIMIT
    assert service._capped_limit(MAX_RANKING_LIMIT + 50) == MAX_RANKING_LIMIT


@pytest.mark.asyncio()
async def test_every_exportable_report_renders_without_touch_the_database() -> None:
    """Each branch builds its own rows; a branch nobody ran rots silently."""
    service = _service(
        _StubRepository(
            host_status={"ONLINE": 2},
            trend=({}, {}),
            availability_rows=[
                (1, "CH_A", "网关", "https://a", 10, 1, 12.5, 40.0)
            ],
        )
    )
    for report in ("summary", "alert-trend", "alert-ranking", "availability", "host-status"):
        exported = await service.export(report=report, days=7)
        assert exported.report == report
        assert exported.filename.startswith(f"ops-{report}-")
        # The BOM belongs to the download, not to the document: a test that
        # asserts on the text would otherwise pass only by accident.
        assert not exported.content.startswith("\ufeff")
        lines = exported.content.splitlines()
        assert len(lines) >= 1
        columns = lines[0].count(",") + 1
        assert all(line.count(",") + 1 == columns for line in lines), report


def test_csv_escapes_a_value_that_contains_a_comma_or_a_quote() -> None:
    rendered = _render_csv(
        ["名称", "备注"], [["网关,主", '他说 "上线" 了'], ["普通", "plain"]]
    )

    # CRLF line endings are what Excel expects; the quotes round-trip intact.
    assert rendered.splitlines()[0] == "名称,备注"
    assert rendered.splitlines()[1] == '"网关,主","他说 ""上线"" 了"'
    assert rendered.splitlines()[2] == "普通,plain"
    assert rendered.endswith("\r\n")
