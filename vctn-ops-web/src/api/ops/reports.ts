/** Operations reports (`app/ops/reports`). */

import { get } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type {
  AlertRanking,
  AlertTrend,
  ExportableReport,
  HostStatusDistribution,
  ReportAvailability,
  ReportExport,
  ReportSummary,
} from '@/types/ops'

/** Longest window the backend accepts (`MAX_REPORT_DAYS`). */
export const MAX_REPORT_DAYS = 180

/** Windows offered by every report page, in days. */
export const REPORT_WINDOWS: readonly number[] = [1, 7, 30, 90]

/** Default window, matching `DEFAULT_REPORT_DAYS` on the backend. */
export const DEFAULT_REPORT_DAYS = 7

/** `GET /ops/reports/summary` */
export function fetchReportSummary(days = DEFAULT_REPORT_DAYS): Promise<ReportSummary> {
  return get<ReportSummary>(opsPath('/reports/summary'), { params: { days } })
}

/** `GET /ops/reports/alert-trend` */
export function fetchAlertTrend(days = DEFAULT_REPORT_DAYS): Promise<AlertTrend> {
  return get<AlertTrend>(opsPath('/reports/alert-trend'), { params: { days } })
}

/** `GET /ops/reports/alert-ranking` */
export function fetchAlertRanking(days = DEFAULT_REPORT_DAYS, limit = 10): Promise<AlertRanking> {
  return get<AlertRanking>(opsPath('/reports/alert-ranking'), {
    params: { days, limit },
  })
}

/** `GET /ops/reports/availability` */
export function fetchReportAvailability(
  days = DEFAULT_REPORT_DAYS,
): Promise<ReportAvailability> {
  return get<ReportAvailability>(opsPath('/reports/availability'), { params: { days } })
}

/** `GET /ops/reports/host-status` */
export function fetchHostStatus(
  days = DEFAULT_REPORT_DAYS,
): Promise<HostStatusDistribution> {
  return get<HostStatusDistribution>(opsPath('/reports/host-status'), { params: { days } })
}

/** `GET /ops/reports/export` — the CSV body travels inside the envelope. */
export function exportReport(
  report: ExportableReport = 'summary',
  days = DEFAULT_REPORT_DAYS,
  limit = 10,
): Promise<ReportExport> {
  return get<ReportExport>(opsPath('/reports/export'), {
    params: { report, days, limit },
  })
}

/**
 * Turn an exported CSV into a Blob the browser will save with a sane name.
 *
 * The BOM is added here rather than on the server: the envelope carries the
 * document as plain text, and Excel on Windows only reads UTF-8 correctly when
 * the file opens with one.
 */
export function csvToBlob(content: string, contentType = 'text/csv; charset=utf-8'): Blob {
  return new Blob(['\uFEFF', content], { type: contentType })
}
