/** Public tool catalogue used by the admin pickers (`app/tools/catalog`). */

import { get } from '@/api/client'
import type { Tool, ToolCategory, PopularTool, RecentTool } from '@/types/tools'

/** `GET /tool-categories` */
export function listCategories(): Promise<ToolCategory[]> {
  return get<ToolCategory[]>('/tool-categories')
}

/** `GET /tools` */
export function listTools(categoryId?: string): Promise<Tool[]> {
  return get<Tool[]>('/tools', { params: categoryId ? { category_id: categoryId } : {} })
}

/** `GET /tools/{tool_id}` */
export function getTool(toolId: string): Promise<Tool> {
  return get<Tool>(`/tools/${toolId}`)
}

/** `GET /tools/by-slug/{slug}` */
export function getToolBySlug(slug: string): Promise<Tool> {
  return get<Tool>(`/tools/by-slug/${encodeURIComponent(slug)}`)
}

/** `GET /tools/popular` */
export function listPopularTools(windowDays = 7, limit = 10): Promise<PopularTool[]> {
  return get<PopularTool[]>('/tools/popular', {
    params: { window_days: windowDays, limit },
  })
}

/** `GET /tools/recent` */
export function listRecentTools(limit = 10): Promise<RecentTool[]> {
  return get<RecentTool[]>('/tools/recent', { params: { limit } })
}

/** `GET /tools/search` */
export function searchTools(keyword: string): Promise<Tool[]> {
  return get<Tool[]>('/tools/search', { params: { keyword } })
}
