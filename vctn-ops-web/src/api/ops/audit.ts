/**
 * The ops audit trail (`app/ops/audit`).
 *
 * Read-only by design: the trail is append-only, so this module exposes no
 * create, update or delete call.
 */

import { get } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { OpsAuditRecord } from '@/types/ops'

/** Filters accepted by `GET /ops/audit`. */
export interface AuditFilters {
  action?: string
  resourceType?: string
  operatorUsername?: string
  result?: string
  traceId?: string
  startAt?: Date | string | null
  endAt?: Date | string | null
}

/** `GET /ops/audit` */
export function listAuditRecords(
  page = 1,
  pageSize = 20,
  filters: AuditFilters = {},
): Promise<Page<OpsAuditRecord>> {
  return get<Page<OpsAuditRecord>>(opsPath('/audit'), {
    params: {
      page,
      page_size: pageSize,
      action: filters.action ?? undefined,
      resource_type: filters.resourceType ?? undefined,
      operator_username: filters.operatorUsername ?? undefined,
      result: filters.result ?? undefined,
      trace_id: filters.traceId ?? undefined,
      start_at: toIsoDateTime(filters.startAt),
      end_at: toIsoDateTime(filters.endAt),
    },
  })
}

/** `GET /ops/audit/{record_id}` */
export function getAuditRecord(recordId: string): Promise<OpsAuditRecord> {
  return get<OpsAuditRecord>(opsPath(`/audit/${encodeURIComponent(recordId)}`))
}
