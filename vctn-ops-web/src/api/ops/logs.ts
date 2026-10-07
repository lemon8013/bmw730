/**
 * The unified ops log search (`app/ops/logs`).
 *
 * The four streams stay separate tables on the backend; this module projects
 * them onto one redacted shape, so one screen can search all of them and
 * reconstruct a trace. Nothing here carries a raw request or response body.
 */

import { get } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { LogContext, LogEntry } from '@/types/ops'
import { DEFAULT_LOG_TYPE, type LogType } from '@/types/enums'

/** Filters accepted by `GET /ops/logs`. */
export interface LogFilters {
  logType: LogType
  level?: string
  service?: string
  traceId?: string
  requestId?: string
  keyword?: string
  ip?: string
  startAt?: Date | string | null
  endAt?: Date | string | null
}

/** `GET /ops/logs` */
export function searchLogs(
  page = 1,
  pageSize = 20,
  filters: Partial<LogFilters> = {},
): Promise<Page<LogEntry>> {
  return get<Page<LogEntry>>(opsPath('/logs'), {
    params: {
      page,
      page_size: pageSize,
      log_type: filters.logType ?? DEFAULT_LOG_TYPE,
      level: filters.level ?? undefined,
      service: filters.service ?? undefined,
      trace_id: filters.traceId ?? undefined,
      request_id: filters.requestId ?? undefined,
      keyword: filters.keyword ?? undefined,
      ip: filters.ip ?? undefined,
      start_at: toIsoDateTime(filters.startAt),
      end_at: toIsoDateTime(filters.endAt),
    },
  })
}

/** `GET /ops/logs/context` — every record of one trace, oldest first. */
export function fetchLogContext(traceId: string, limit = 100): Promise<LogContext> {
  return get<LogContext>(opsPath('/logs/context'), { params: { trace_id: traceId, limit } })
}

/** `GET /ops/logs/{log_id}` */
export function getLog(logId: string, logType: LogType = DEFAULT_LOG_TYPE): Promise<LogEntry> {
  return get<LogEntry>(opsPath(`/logs/${encodeURIComponent(logId)}`), {
    params: { log_type: logType },
  })
}
