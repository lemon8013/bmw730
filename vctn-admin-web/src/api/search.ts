/** Unified site search (`app/system/search`). */

import { get } from '@/api/client'
import type { SearchResultItem } from '@/types/ops'

/** `GET /search` */
export function searchSite(query: string, type?: string): Promise<SearchResultItem[]> {
  return get<SearchResultItem[]>('/search', {
    params: type ? { q: query, type } : { q: query },
  })
}
