/** Feature flag administration (`app/admin/config`). */

import { get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateFeatureFlagRequest,
  FeatureFlag,
  UpdateFeatureFlagRequest,
} from '@/types/system'

/** `GET /admin/feature-flags` */
export function listFeatureFlags(page = 1, pageSize = 200): Promise<Page<FeatureFlag>> {
  return get<Page<FeatureFlag>>('/admin/feature-flags', {
    params: { page, page_size: pageSize },
  })
}

/** `POST /admin/feature-flags` */
export function createFeatureFlag(payload: CreateFeatureFlagRequest): Promise<FeatureFlag> {
  return post<FeatureFlag>('/admin/feature-flags', payload, {
    vctn: { idempotencyKey: `create-flag:${payload.flag_key}` },
  })
}

/** `PUT /admin/feature-flags/{flag_id}` */
export function updateFeatureFlag(
  flagId: string,
  payload: UpdateFeatureFlagRequest,
): Promise<FeatureFlag> {
  return put<FeatureFlag>(`/admin/feature-flags/${flagId}`, payload)
}

/** `POST /admin/feature-flags/{flag_id}/enable` */
export function enableFeatureFlag(flagId: string): Promise<FeatureFlag> {
  return post<FeatureFlag>(`/admin/feature-flags/${flagId}/enable`)
}

/** `POST /admin/feature-flags/{flag_id}/disable` */
export function disableFeatureFlag(flagId: string): Promise<FeatureFlag> {
  return post<FeatureFlag>(`/admin/feature-flags/${flagId}/disable`)
}
