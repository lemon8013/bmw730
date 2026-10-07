"""app.ops.reports — business logic.

Every report is a read-only projection, so nothing here opens a transaction:
the module never writes and therefore never commits. That is deliberate — a
report that mutated its input would make "open two tabs" unsafe.

Two rules keep the numbers honest and are worth repeating:

* a report is **total**: no data yields zeros and empty rows, never an error;
* the trend axis is **dense**: every day of the window appears, because a chart
  with holes makes a window look calmer than it was.
"""

from __future__ import annotations

import csv
import datetime
import io

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.ops.reports.repository import ReportRepository
from app.ops.reports.schema import (
    ABNORMAL_SERVICE_STATUSES,
    ACTIVE_ALERT_STATUSES,
    AGENT_STATUS_ONLINE,
    DEFAULT_RANKING_LIMIT,
    EXPORTABLE_REPORTS,
    HOST_STATUS_ONLINE,
    MAX_RANKING_LIMIT,
    REPORT_SEVERITIES,
    SEVERITY_RANK,
    AgentReport,
    AlertRankingResponse,
    AlertRankingRow,
    AlertReport,
    AlertTrendPoint,
    AlertTrendResponse,
    AvailabilityReport,
    AvailabilityReportResponse,
    AvailabilityRow,
    HostReport,
    HostStatusResponse,
    HostStatusRow,
    ReportExportResponse,
    ReportSummaryResponse,
    ReportWindow,
    ServiceReport,
)


class ReportService:
    """The operations reports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ReportRepository(session)

    # -- 公共读路径 ---------------------------------------------------

    async def summary(self, *, days: int) -> ReportSummaryResponse:
        now = datetime.datetime.now(datetime.UTC)
        window = self._window(now, days)

        by_status = await self._repository.count_hosts_by_status()
        host_total = sum(by_status.values())
        host_online = by_status.get(HOST_STATUS_ONLINE, 0)

        service_total, service_abnormal, service_availability = (
            await self._repository.aggregate_services(
                abnormal_statuses=ABNORMAL_SERVICE_STATUSES
            )
        )
        fired, resolved, active, raw_severities, mttr = await self._repository.aggregate_alerts(
            since=window.start_at, active_statuses=ACTIVE_ALERT_STATUSES
        )
        by_severity = {severity: 0 for severity in sorted(REPORT_SEVERITIES)}
        for severity, count in raw_severities.items():
            by_severity[severity] = by_severity.get(severity, 0) + count

        check_count, failure_count = await self._repository.aggregate_availability(
            since=window.start_at
        )
        agent_total, agent_online = await self._repository.aggregate_agents(
            online_status=AGENT_STATUS_ONLINE
        )

        return ReportSummaryResponse(
            window=window,
            host=HostReport(
                total=host_total,
                online=host_online,
                by_status=by_status,
                online_rate=host_online / host_total if host_total else 0.0,
            ),
            service=ServiceReport(
                total=service_total,
                abnormal=service_abnormal,
                availability_rate=service_availability,
            ),
            alert=AlertReport(
                fired=fired,
                resolved=resolved,
                active=active,
                by_severity=by_severity,
                resolve_rate=resolved / fired if fired else 0.0,
                mttr_seconds=mttr,
            ),
            availability=AvailabilityReport(
                check_count=check_count,
                failure_count=failure_count,
                success_rate=(check_count - failure_count) / check_count
                if check_count
                else 0.0,
            ),
            agent=AgentReport(total=agent_total, online=agent_online),
            generated_at=now,
        )

    async def alert_trend(self, *, days: int) -> AlertTrendResponse:
        now = datetime.datetime.now(datetime.UTC)
        window = self._window(now, days)

        fired, resolved = await self._repository.alert_trend(since=window.start_at)
        points: list[AlertTrendPoint] = []
        for day in self._days_of(window):
            buckets = fired.get(day, {})
            by_severity = {severity: 0 for severity in sorted(REPORT_SEVERITIES)}
            for severity, count in buckets.items():
                by_severity[severity] = by_severity.get(severity, 0) + count
            points.append(
                AlertTrendPoint(
                    date=day,
                    fired=sum(by_severity.values()),
                    resolved=resolved.get(day, 0),
                    by_severity=by_severity,
                )
            )
        return AlertTrendResponse(window=window, points=points, generated_at=now)

    async def alert_ranking(self, *, days: int, limit: int = 0) -> AlertRankingResponse:
        now = datetime.datetime.now(datetime.UTC)
        window = self._window(now, days)
        capped = self._capped_limit(limit)
        rows = await self._repository.alert_ranking(since=window.start_at, limit=capped)
        return AlertRankingResponse(
            window=window,
            rows=[
                AlertRankingRow(
                    rank=index,
                    resource_type=resource_type,
                    resource_id=None if resource_id is None else str(resource_id),
                    alert_type=alert_type,
                    total=total,
                    active=active,
                    worst_severity=SEVERITY_RANK.get(worst_rank),
                    last_triggered_at=last_triggered_at,
                )
                for index, (
                    resource_type,
                    resource_id,
                    alert_type,
                    total,
                    active,
                    worst_rank,
                    last_triggered_at,
                ) in enumerate(rows, start=1)
            ],
            generated_at=now,
        )

    async def availability(self, *, days: int) -> AvailabilityReportResponse:
        now = datetime.datetime.now(datetime.UTC)
        window = self._window(now, days)
        rows = await self._repository.availability_rows(since=window.start_at)
        return AvailabilityReportResponse(
            window=window,
            rows=[
                AvailabilityRow(
                    check_id=str(int(check_id)),
                    check_code=str(check_code),
                    name=str(name),
                    target=str(target),
                    total=int(total),
                    failed=int(failed),
                    success_rate=(total - failed) / total if total else 0.0,
                    avg_latency_ms=float(avg_latency or 0.0),
                    max_latency_ms=float(max_latency or 0.0),
                )
                for (
                    check_id,
                    check_code,
                    name,
                    target,
                    total,
                    failed,
                    avg_latency,
                    max_latency,
                ) in rows
            ],
            generated_at=now,
        )

    async def host_status(self, *, days: int) -> HostStatusResponse:
        now = datetime.datetime.now(datetime.UTC)
        window = self._window(now, days)
        by_status = await self._repository.count_hosts_by_status()
        total = sum(by_status.values())
        return HostStatusResponse(
            window=window,
            total=total,
            rows=[
                HostStatusRow(
                    status=status,
                    count=count,
                    share=count / total if total else 0.0,
                )
                for status, count in sorted(
                    by_status.items(), key=lambda item: (-item[1], item[0])
                )
            ],
            generated_at=now,
        )

    # -- 导出 ---------------------------------------------------------

    async def export(
        self, *, report: str, days: int, limit: int = 0
    ) -> ReportExportResponse:
        """把一个报表渲染成 CSV。

        报表正文随信封返回，而不是裸 `text/csv`：本 API 的每一个响应都包信封，
        前端共享客户端遇到没有信封的响应会直接判为坏响应。
        """
        name = report.strip().lower()
        if name not in EXPORTABLE_REPORTS:
            raise ValidationError(f"unsupported report: {report}")
        now = datetime.datetime.now(datetime.UTC)
        header, rows = await self._to_rows(report=name, days=days, limit=limit)
        return ReportExportResponse(
            report=name,
            filename=f"ops-{name}-{days}d-{now.strftime('%Y%m%d%H%M%S')}.csv",
            content=_render_csv(header, rows),
            generated_at=now,
        )

    async def _to_rows(
        self, *, report: str, days: int, limit: int
    ) -> tuple[list[str], list[list[str]]]:
        if report == "summary":
            summary = await self.summary(days=days)
            return ["指标", "值"], [
                ["主机总数", str(summary.host.total)],
                ["主机在线", str(summary.host.online)],
                ["主机在线率", f"{summary.host.online_rate:.4f}"],
                ["服务总数", str(summary.service.total)],
                ["异常服务", str(summary.service.abnormal)],
                ["服务可用率", f"{summary.service.availability_rate:.4f}"],
                ["告警触发", str(summary.alert.fired)],
                ["告警恢复", str(summary.alert.resolved)],
                ["当前活跃告警", str(summary.alert.active)],
                ["告警恢复率", f"{summary.alert.resolve_rate:.4f}"],
                [
                    "MTTR(秒)",
                    ""
                    if summary.alert.mttr_seconds is None
                    else f"{summary.alert.mttr_seconds:.1f}",
                ],
                ["可用性探测次数", str(summary.availability.check_count)],
                ["可用性成功率", f"{summary.availability.success_rate:.4f}"],
                ["Agent 总数", str(summary.agent.total)],
                ["Agent 在线", str(summary.agent.online)],
            ]
        if report == "alert-trend":
            trend = await self.alert_trend(days=days)
            severities = sorted(REPORT_SEVERITIES)
            header = ["日期", "触发", "恢复"] + [f"级别_{s}" for s in severities]
            return header, [
                [point.date, str(point.fired), str(point.resolved)]
                + [str(point.by_severity.get(severity, 0)) for severity in severities]
                for point in trend.points
            ]
        if report == "alert-ranking":
            ranking = await self.alert_ranking(days=days, limit=limit)
            header = [
                "排名",
                "资源类型",
                "资源ID",
                "告警类型",
                "总数",
                "活跃",
                "最严重级别",
                "最后触发",
            ]
            return header, [
                [
                    str(row.rank),
                    row.resource_type,
                    row.resource_id or "",
                    row.alert_type,
                    str(row.total),
                    str(row.active),
                    row.worst_severity or "",
                    "" if row.last_triggered_at is None else row.last_triggered_at.isoformat(),
                ]
                for row in ranking.rows
            ]
        if report == "availability":
            availability = await self.availability(days=days)
            header = [
                "编码",
                "名称",
                "目标",
                "探测次数",
                "失败次数",
                "成功率",
                "平均耗时(ms)",
                "最大耗时(ms)",
            ]
            return header, [
                [
                    row.check_code,
                    row.name,
                    row.target,
                    str(row.total),
                    str(row.failed),
                    f"{row.success_rate:.4f}",
                    f"{row.avg_latency_ms:.2f}",
                    f"{row.max_latency_ms:.2f}",
                ]
                for row in availability.rows
            ]
        distribution = await self.host_status(days=days)
        return ["主机状态", "数量", "占比"], [
            [row.status, str(row.count), f"{row.share:.4f}"] for row in distribution.rows
        ]

    # -- 内部辅助 -----------------------------------------------------

    def _window(self, now: datetime.datetime, days: int) -> ReportWindow:
        return ReportWindow(
            days=days,
            start_at=now - datetime.timedelta(days=days),
            end_at=now,
        )

    def _days_of(self, window: ReportWindow) -> list[str]:
        """窗口内每一天（含首尾），按 UTC 排序去重的 `YYYY-MM-DD`。

        触发桶与恢复桶的键来自不同的日期集合，只有"遍历窗口"才能保证没有
        某一天被漏掉。
        """
        start_day = window.start_at.date()
        days = (window.end_at.date() - start_day).days + 1
        return [
            (start_day + datetime.timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range(max(days, 1))
        ]

    def _capped_limit(self, limit: int) -> int:
        """`limit` 缺省时回落到枚举默认值，且永不超过上限。"""
        if limit <= 0:
            return DEFAULT_RANKING_LIMIT
        return min(limit, MAX_RANKING_LIMIT)


def _render_csv(header: list[str], rows: list[list[str]]) -> str:
    """Render CSV with the quoting Excel expects for Chinese text."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()
