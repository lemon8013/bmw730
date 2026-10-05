/**
 * Tool catalogue wire format (`app/tools/catalog`).
 *
 * The final Tool API DTO is not frozen; these interfaces mirror what the
 * backend answers today so the UI has one typed boundary.
 */

import type { EntityId } from '@/types/api'
import type { ToolExecutionMode } from '@/types/tool'

/** One tool category. */
export interface ToolCategoryItem {
  readonly id: EntityId
  readonly category_code: string
  readonly category_name: string
  readonly description: string | null
  readonly icon_url: string | null
  readonly sort_order: number
  readonly status: string
}

/** One catalogue tool. */
export interface ToolCatalogItem {
  readonly id: EntityId
  readonly code: string
  readonly name: string
  readonly slug: string
  readonly category_id: EntityId | null
  readonly icon: string | null
  readonly summary: string | null
  readonly description: string | null
  readonly keywords: readonly string[]
  readonly tags: readonly string[]
  readonly component_key: string
  readonly execution_mode: ToolExecutionMode
  readonly status: string
  readonly sort_order: number
  readonly current_version_id: EntityId | null
}

/** One entry of the popularity ranking (`GET /tools/popular`). */
export interface PopularToolItem {
  readonly tool_id: EntityId
  readonly tool_name: string | null
  readonly tool_slug: string | null
  readonly usage_count: number
  readonly unique_user_count: number
  readonly rank_no: number | null
  readonly score: number | null
}
