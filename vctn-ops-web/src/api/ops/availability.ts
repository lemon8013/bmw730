/** Availability probes and their results (`app/ops/availability`). */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  AvailabilityCheck,
  AvailabilityCheckCreateRequest,
  AvailabilityCheckUpdateRequest,
  AvailabilityResult,
} from '@/types/ops'

/** Filters accepted by `GET /ops/availability`. */
export interface AvailabilityFilters {
  keyword?: string
  checkType?: string
  serviceId?: string
  environment?: string
  enabled?: boolean
}

/** `GET /ops/availability` */
export function listAvailabilityChecks(
  page = 1,
  pageSize = 20,
  filters: AvailabilityFilters = {},
): Promise<Page<AvailabilityCheck>> {
  return get<Page<AvailabilityCheck>>(opsPath('/availability'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      check_type: filters.checkType ?? undefined,
      service_id: filters.serviceId ?? undefined,
      environment: filters.environment ?? undefined,
      enabled: filters.enabled ?? undefined,
    },
  })
}

/** `POST /ops/availability` — requires `OPS_MONITOR_MANAGE`. */
export function createAvailabilityCheck(
  payload: AvailabilityCheckCreateRequest,
): Promise<AvailabilityCheck> {
  return post<AvailabilityCheck>(opsPath('/availability'), payload)
}

/** `GET /ops/availability/{check_id}` */
export function getAvailabilityCheck(checkId: string): Promise<AvailabilityCheck> {
  return get<AvailabilityCheck>(opsPath(`/availability/${encodeURIComponent(checkId)}`))
}

/** `PUT /ops/availability/{check_id}` — requires `OPS_MONITOR_MANAGE`. */
export function updateAvailabilityCheck(
  checkId: string,
  payload: AvailabilityCheckUpdateRequest,
): Promise<AvailabilityCheck> {
  return put<AvailabilityCheck>(opsPath(`/availability/${encodeURIComponent(checkId)}`), payload)
}

/** `DELETE /ops/availability/{check_id}` — requires `OPS_MONITOR_MANAGE`. */
export function deleteAvailabilityCheck(checkId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/availability/${encodeURIComponent(checkId)}`))
}

/** `GET /ops/availability/{check_id}/results` */
export function listAvailabilityResults(
  checkId: string,
  page = 1,
  pageSize = 20,
  hours = 24,
  success?: boolean,
): Promise<Page<AvailabilityResult>> {
  return get<Page<AvailabilityResult>>(
    opsPath(`/availability/${encodeURIComponent(checkId)}/results`),
    { params: { page, page_size: pageSize, hours, success: success ?? undefined } },
  )
}
