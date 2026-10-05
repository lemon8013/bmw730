/** System configuration mirror (`app/admin/config`). */

import { get, put } from '@/api/client'
import type { Page } from '@/types/api'
import type { SystemConfig, UpdateConfigRequest } from '@/types/system'

/** `GET /admin/config` */
export function listConfigs(page = 1, pageSize = 200): Promise<Page<SystemConfig>> {
  return get<Page<SystemConfig>>('/admin/config', { params: { page, page_size: pageSize } })
}

/** `PUT /admin/config/{config_key}` */
export function updateConfig(
  configKey: string,
  payload: UpdateConfigRequest,
): Promise<SystemConfig> {
  return put<SystemConfig>(`/admin/config/${encodeURIComponent(configKey)}`, payload)
}
