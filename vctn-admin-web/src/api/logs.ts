/** Unified log console (`app/admin/logs`). */

import { get, post } from '@/api/client'
import type { Page } from '@/types/api'
import type { AnyLogRow, LogsSummary, UnifiedLogQuery } from '@/types/audit'
import type { LogType } from '@/types/enums'
import type { ExportTask } from '@/types/ops'

/** `GET /admin/logs` */
export function fetchLogsSummary(): Promise<LogsSummary> {
  return get<LogsSummary>('/admin/logs')
}

/** `GET /admin/logs/{log_type}` */
export function queryLogs(
  logType: LogType,
  query: UnifiedLogQuery = {},
): Promise<Page<AnyLogRow>> {
  return get<Page<AnyLogRow>>(`/admin/logs/${logType}`, { params: query })
}

/** `POST /admin/logs/{log_type}/export` */
export function exportLogs(logType: LogType, query: UnifiedLogQuery = {}): Promise<ExportTask> {
  return post<ExportTask>(`/admin/logs/${logType}/export`, undefined, { params: query })
}
