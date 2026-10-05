/** Trace aggregation (`app/admin/audit`, `app/admin/logs`). */

import { get } from '@/api/client'
import type { TraceDetail } from '@/types/audit'

/** `GET /admin/traces/{trace_id}` */
export function getTrace(traceId: string): Promise<TraceDetail> {
  return get<TraceDetail>(`/admin/traces/${traceId}`)
}

/** `GET /admin/logs/audit/traces/{trace_id}` */
export function getLogTrace(traceId: string): Promise<TraceDetail> {
  return get<TraceDetail>(`/admin/logs/audit/traces/${traceId}`)
}
