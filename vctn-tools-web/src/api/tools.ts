/** Tool catalogue, execution and job clients (`app/tools`). */

import { httpClient } from '@/api/client'
import type { ApiEnvelope } from '@/types/api'
import type { PopularToolItem, ToolCatalogItem, ToolCategoryItem } from '@/types/catalog'
import type { ToolExecuteRequest, ToolExecuteResponse, ToolJobItem } from '@/types/execution'

async function unwrap<T>(path: string): Promise<T> {
  const response = await httpClient.get<ApiEnvelope<T>>(path)
  const envelope = response.data
  if (envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message)
  }
  return envelope.data
}

/** `GET /tool-categories` */
export function listToolCategories(): Promise<ToolCategoryItem[]> {
  return unwrap<ToolCategoryItem[]>('/tool-categories')
}

/** `GET /tools` — omit `categoryId` for the whole catalogue. */
export function listTools(categoryId?: string): Promise<ToolCatalogItem[]> {
  const query = categoryId === undefined ? '' : `?category_id=${encodeURIComponent(categoryId)}`
  return unwrap<ToolCatalogItem[]>(`/tools${query}`)
}

/** `GET /tools/popular` */
export function popularTools(windowDays = 7, limit = 20): Promise<PopularToolItem[]> {
  return unwrap<PopularToolItem[]>(`/tools/popular?window_days=${windowDays}&limit=${limit}`)
}

/** `GET /tools/search` */
export function searchTools(keyword: string): Promise<ToolCatalogItem[]> {
  return unwrap<ToolCatalogItem[]>(`/tools/search?keyword=${encodeURIComponent(keyword)}`)
}

/** `GET /tools/by-slug/{slug}` */
export function toolBySlug(slug: string): Promise<ToolCatalogItem> {
  return unwrap<ToolCatalogItem>(`/tools/by-slug/${encodeURIComponent(slug)}`)
}

/** `POST /tools/runtime/execute/{tool_id}` */
export async function executeTool(
  toolId: string,
  request: ToolExecuteRequest,
): Promise<ToolExecuteResponse> {
  const response = await httpClient.post<ApiEnvelope<ToolExecuteResponse>>(
    `/tools/runtime/execute/${encodeURIComponent(toolId)}`,
    request,
  )
  const envelope = response.data
  if (envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message)
  }
  return envelope.data
}

/** `GET /tools/jobs/{job_id}` */
export function getToolJob(jobId: string): Promise<ToolJobItem> {
  return unwrap<ToolJobItem>(`/tools/jobs/${encodeURIComponent(jobId)}`)
}
