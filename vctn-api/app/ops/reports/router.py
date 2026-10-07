"""app.ops.reports — HTTP endpoints.

Every endpoint is read-only and every endpoint answers the same question with
the same shape: *what happened in this window*. They all require
``OPS_REPORT_VIEW``, enforced by the backend ``AuthorizationService`` — the
console hides what the caller cannot open, but only the backend decides.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.reports.schema import (
    DEFAULT_RANKING_LIMIT,
    DEFAULT_REPORT_DAYS,
    MAX_RANKING_LIMIT,
    MAX_REPORT_DAYS,
    AlertRankingResponse,
    AlertTrendResponse,
    AvailabilityReportResponse,
    HostStatusResponse,
    ReportExportResponse,
    ReportSummaryResponse,
)
from app.ops.reports.service import ReportService
from app.shared.authorization.dependencies import require_permission
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> ReportService:
    return ReportService(session)


@router.get(
    "/reports/summary",
    response_model=ApiResponse[ReportSummaryResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def get_summary(
    session: DbSessionDep,
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
) -> ApiResponse[ReportSummaryResponse]:
    """Headline numbers of the reporting window."""
    return success(await _service(session).summary(days=days))


@router.get(
    "/reports/alert-trend",
    response_model=ApiResponse[AlertTrendResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def get_alert_trend(
    session: DbSessionDep,
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
) -> ApiResponse[AlertTrendResponse]:
    """Daily alert volume; every day of the window is present."""
    return success(await _service(session).alert_trend(days=days))


@router.get(
    "/reports/alert-ranking",
    response_model=ApiResponse[AlertRankingResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def get_alert_ranking(
    session: DbSessionDep,
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
    limit: int = Query(default=DEFAULT_RANKING_LIMIT, ge=1, le=MAX_RANKING_LIMIT),
) -> ApiResponse[AlertRankingResponse]:
    """The noisiest resources inside the window, most alerts first."""
    return success(await _service(session).alert_ranking(days=days, limit=limit))


@router.get(
    "/reports/availability",
    response_model=ApiResponse[AvailabilityReportResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def get_availability(
    session: DbSessionDep,
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
) -> ApiResponse[AvailabilityReportResponse]:
    """Per-probe availability, least reliable first."""
    return success(await _service(session).availability(days=days))


@router.get(
    "/reports/host-status",
    response_model=ApiResponse[HostStatusResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def get_host_status(
    session: DbSessionDep,
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
) -> ApiResponse[HostStatusResponse]:
    """Host fleet status distribution."""
    return success(await _service(session).host_status(days=days))


@router.get(
    "/reports/export",
    response_model=ApiResponse[ReportExportResponse],
    dependencies=[Depends(require_permission("OPS_REPORT_VIEW"))],
)
async def export_report(
    session: DbSessionDep,
    report: str = Query(default="summary"),
    days: int = Query(default=DEFAULT_REPORT_DAYS, ge=1, le=MAX_REPORT_DAYS),
    limit: int = Query(default=DEFAULT_RANKING_LIMIT, ge=1, le=MAX_RANKING_LIMIT),
) -> ApiResponse[ReportExportResponse]:
    """Render one report as CSV inside the envelope."""
    return success(await _service(session).export(report=report, days=days, limit=limit))
