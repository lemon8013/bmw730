/** Tool administration (`app/admin/tools`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  AccessPolicyRequest,
  AdminAccessPolicy,
  Tool,
  ToolCategory,
  ToolCategoryCreateRequest,
  ToolCategoryUpdateRequest,
  ToolCreateRequest,
  ToolStatusRequest,
  ToolUpdateRequest,
  ToolUsageAdmin,
  ToolUsageOverviewAdmin,
  ToolUsagePointAdmin,
  ToolUsageTrendPointAdmin,
  ToolVisibility,
  ToolVisibilityRequest,
} from '@/types/tools'

/** `GET /admin/tools` */
export function listAdminTools(query: {
  status?: string
  category_id?: string
  keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<Page<Tool>> {
  return get<Page<Tool>>('/admin/tools', { params: query })
}

/** `POST /admin/tools` */
export function createTool(payload: ToolCreateRequest): Promise<Tool> {
  return post<Tool>('/admin/tools', payload, {
    vctn: { idempotencyKey: `create-tool:${payload.code}` },
  })
}

/** `GET /admin/tools/{tool_id}` */
export function getAdminTool(toolId: string): Promise<Tool> {
  return get<Tool>(`/admin/tools/${toolId}`)
}

/** `PUT /admin/tools/{tool_id}` */
export function updateTool(toolId: string, payload: ToolUpdateRequest): Promise<Tool> {
  return put<Tool>(`/admin/tools/${toolId}`, payload)
}

/** `PUT /admin/tools/{tool_id}/status` */
export function setToolStatus(toolId: string, payload: ToolStatusRequest): Promise<Tool> {
  return put<Tool>(`/admin/tools/${toolId}/status`, payload)
}

/** `GET /admin/tools/usage` — usage counts per tool. */
export function listToolUsage(days = 30): Promise<ToolUsageAdmin[]> {
  return get<ToolUsageAdmin[]>('/admin/tools/usage', { params: { days } })
}

/** `GET /admin/tools/usage/daily` — one tool's usage per day. */
export function getToolUsageDaily(toolId: string, days = 30): Promise<ToolUsagePointAdmin[]> {
  return get<ToolUsagePointAdmin[]>('/admin/tools/usage/daily', {
    params: { tool_id: toolId, days },
  })
}

/** `GET /admin/tools/usage/overview` — window wide totals. */
export function getToolUsageOverview(days = 30): Promise<ToolUsageOverviewAdmin> {
  return get<ToolUsageOverviewAdmin>('/admin/tools/usage/overview', { params: { days } })
}

/** `GET /admin/tools/usage/trend` — platform wide usage per day. */
export function getToolUsageTrend(days = 30): Promise<ToolUsageTrendPointAdmin[]> {
  return get<ToolUsageTrendPointAdmin[]>('/admin/tools/usage/trend', { params: { days } })
}

/** `GET /admin/tools/categories` — includes DISABLED rows by default. */
export function listAdminCategories(includeDisabled = true): Promise<ToolCategory[]> {
  return get<ToolCategory[]>('/admin/tools/categories', {
    params: { include_disabled: includeDisabled },
  })
}

/** `POST /admin/tools/categories` */
export function createToolCategory(
  payload: ToolCategoryCreateRequest,
): Promise<ToolCategory> {
  return post<ToolCategory>('/admin/tools/categories', payload)
}

/** `PUT /admin/tools/categories/{category_id}` */
export function updateToolCategory(
  categoryId: string,
  payload: ToolCategoryUpdateRequest,
): Promise<ToolCategory> {
  return put<ToolCategory>(`/admin/tools/categories/${categoryId}`, payload)
}

/** `DELETE /admin/tools/categories/{category_id}` */
export function deleteToolCategory(categoryId: string): Promise<null> {
  return del<null>(`/admin/tools/categories/${categoryId}`)
}

/** `GET /admin/tools/visibility` */
export function listToolVisibility(): Promise<ToolVisibility[]> {
  return get<ToolVisibility[]>('/admin/tools/visibility')
}

/** `PUT /admin/tools/visibility/{tool_id}` */
export function setToolVisibility(
  toolId: string,
  payload: ToolVisibilityRequest,
): Promise<ToolVisibility> {
  return put<ToolVisibility>(`/admin/tools/visibility/${toolId}`, payload)
}

/** `GET /admin/tools/access-policies` */
export function listAdminAccessPolicies(): Promise<AdminAccessPolicy[]> {
  return get<AdminAccessPolicy[]>('/admin/tools/access-policies')
}

/** `PUT /admin/tools/access-policies/{tool_id}` */
export function upsertAdminAccessPolicy(
  toolId: string,
  payload: AccessPolicyRequest,
): Promise<AdminAccessPolicy> {
  return put<AdminAccessPolicy>(`/admin/tools/access-policies/${toolId}`, payload)
}
