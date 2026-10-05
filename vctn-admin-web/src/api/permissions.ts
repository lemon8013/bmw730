/** Permission resource administration (`app/admin/permissions`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateResourceRequest,
  PermissionResource,
  PermissionTreeNode,
  UpdateResourceRequest,
} from '@/types/system'

/** `GET /admin/permissions/tree` */
export function fetchPermissionTree(): Promise<PermissionTreeNode[]> {
  return get<PermissionTreeNode[]>('/admin/permissions/tree')
}

/** `GET /admin/permissions/resources` */
export function listPermissionResources(
  page = 1,
  pageSize = 100,
): Promise<Page<PermissionResource>> {
  return get<Page<PermissionResource>>('/admin/permissions/resources', {
    params: { page, page_size: pageSize },
  })
}

/** `POST /admin/permissions/resources` */
export function createPermissionResource(
  payload: CreateResourceRequest,
): Promise<PermissionResource> {
  return post<PermissionResource>('/admin/permissions/resources', payload, {
    vctn: { idempotencyKey: `create-permission:${payload.permission_code}` },
  })
}

/** `PUT /admin/permissions/resources/{resource_id}` */
export function updatePermissionResource(
  resourceId: string,
  payload: UpdateResourceRequest,
): Promise<PermissionResource> {
  return put<PermissionResource>(`/admin/permissions/resources/${resourceId}`, payload)
}

/** `DELETE /admin/permissions/resources/{resource_id}` */
export function deletePermissionResource(resourceId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/permissions/resources/${resourceId}`)
}

/**
 * Load every permission resource, cheapest way that still returns them all.
 *
 * Field policies hang off permission resources, so reading them needs one full
 * listing. The backend caps `page_size`, therefore the listing is walked page
 * by page — but it stops as soon as a page comes back short or empty, so a
 * wrong `total` can never make this loop forever.
 */
export async function listAllPermissionResources(): Promise<PermissionResource[]> {
  const PAGE_SIZE = 200
  const collected: PermissionResource[] = []
  let page = 1
  for (;;) {
    const result = await listPermissionResources(page, PAGE_SIZE)
    const batch = result.items ?? []
    if (batch.length === 0) {
      return collected
    }
    collected.push(...batch)
    if (batch.length < PAGE_SIZE || collected.length >= (result.total ?? 0)) {
      return collected
    }
    page += 1
  }
}
