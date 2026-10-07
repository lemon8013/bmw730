"""Integration tests for the operations reports.

These execute the reports against the **real** PostgreSQL instance. That is not
redundant with the unit suite: the reports are hand written aggregate SQL, and
aggregate SQL has a failure mode no stub can reproduce — it compiles, it binds,
and it only fails once PostgreSQL plans the query.

The case that motivated this file: `date_trunc('day', timezone('UTC', ...))`
rendered in both the select list and the `GROUP BY` becomes two *different*
bind parameters, and PostgreSQL rejects the grouping because `$1` and `$4` are
not the same expression tree. The fix — computing the bucket in a sub-query —
is invisible to a stubbed repository, and only this suite can tell you it works.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.ops.reports.service import ReportService
from app.shared.database.session import build_session_factory

#: Every report the console can open.
REPORTS: tuple[str, ...] = (
    "summary",
    "alert-trend",
    "alert-ranking",
    "availability",
    "host-status",
)


async def _run_reports(settings: Settings, report: str) -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            service = ReportService(session)
            match report:
                case "summary":
                    await service.summary(days=7)
                case "alert-trend":
                    await service.alert_trend(days=30)
                case "alert-ranking":
                    await service.alert_ranking(days=7, limit=10)
                case "availability":
                    await service.availability(days=7)
                case "host-status":
                    await service.host_status(days=7)
                case _:  # pragma: no cover - REPORTS and the cases above agree
                    raise AssertionError(report)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("report", REPORTS)
def test_report_sql_executes_against_postgresql(
    live_infrastructure: None, live_settings: Settings, report: str
) -> None:
    # An empty table is the harder case, not the easier one: a count over zero
    # rows still has to plan, and every rate has to survive dividing by zero.
    asyncio.run(_run_reports(live_settings, report))


def test_every_report_exports_as_csv(
    live_infrastructure: None, live_settings: Settings
) -> None:
    async def run() -> None:
        engine = create_async_engine(live_settings.database_url)
        try:
            async with build_session_factory(engine)() as session:
                service = ReportService(session)
                for report in REPORTS:
                    document = await service.export(report=report, days=7)
                    assert document.report == report
                    # Every row carries the same number of columns as the
                    # header, which is exactly what a hand written CSV gets
                    # wrong when a value contains a comma.
                    lines = document.content.splitlines()
                    assert lines, report
                    width = lines[0].count(",") + 1
                    assert [line.count(",") + 1 for line in lines] == [width] * len(lines)
        finally:
            await engine.dispose()

    asyncio.run(run())
