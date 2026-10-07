/**
 * Maintenance windows (`app/ops/maintenance`).
 *
 * A window silences alert notifications, so writing one is high risk: the write
 * permission is deliberately separate from "may view monitoring".
 */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  MaintenanceWindow,
  MaintenanceWindowCreateRequest,
  MaintenanceWindowUpdateRequest,
} from '@/types/ops'

/** Filters accepted by `GET /ops/maintenance`. */
export interface MaintenanceFilters {
  keyword?: string
  scopeType?: string
  scopeId?: string
  enabled?: boolean
  active?: boolean
}

/** `GET /ops/maintenance` */
export function listMaintenanceWindows(
  page = 1,
  pageSize = 20,
  filters: MaintenanceFilters = {},
): Promise<Page<MaintenanceWindow>> {
  return get<Page<MaintenanceWindow>>(opsPath('/maintenance'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      scope_type: filters.scopeType ?? undefined,
      scope_id: filters.scopeId ?? undefined,
      enabled: filters.enabled ?? undefined,
      active: filters.active ?? undefined,
    },
  })
}

/** `POST /ops/maintenance` — requires `OPS_MAINTENANCE_MANAGE`. */
export function createMaintenanceWindow(
  payload: MaintenanceWindowCreateRequest,
): Promise<MaintenanceWindow> {
  return post<MaintenanceWindow>(opsPath('/maintenance'), payload)
}

/** `GET /ops/maintenance/{window_id}` */
export function getMaintenanceWindow(windowId: string): Promise<MaintenanceWindow> {
  return get<MaintenanceWindow>(opsPath(`/maintenance/${encodeURIComponent(windowId)}`))
}

/** `PUT /ops/maintenance/{window_id}` — requires `OPS_MAINTENANCE_MANAGE`. */
export function updateMaintenanceWindow(
  windowId: string,
  payload: MaintenanceWindowUpdateRequest,
): Promise<MaintenanceWindow> {
  return put<MaintenanceWindow>(opsPath(`/maintenance/${encodeURIComponent(windowId)}`), payload)
}

/** `DELETE /ops/maintenance/{window_id}` — requires `OPS_MAINTENANCE_MANAGE`. */
export function deleteMaintenanceWindow(windowId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/maintenance/${encodeURIComponent(windowId)}`))
}
