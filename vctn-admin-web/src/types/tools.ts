/**
 * Tool platform payloads, matching the schemas under `app/tools`.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

// ---------------------------------------------------------------------------
// Catalogue
// ---------------------------------------------------------------------------

/** `ToolCategoryResponse`. */
export interface ToolCategory {
  id: EntityId
  category_code: string
  category_name: string
  description?: string | null
  icon_url?: string | null
  sort_order: number
  status: string
}

/** `ToolCategoryCreateRequest`. */
export interface ToolCategoryCreateRequest {
  category_code: string
  category_name: string
  description?: string | null
  icon_url?: string | null
  sort_order?: number
  status?: string
}

/** `ToolCategoryUpdateRequest` — `category_code` is immutable after creation. */
export interface ToolCategoryUpdateRequest {
  category_name?: string | null
  description?: string | null
  icon_url?: string | null
  sort_order?: number | null
  status?: string | null
}

/** `ToolResponse`. */
export interface Tool {
  id: EntityId
  code: string
  name: string
  slug: string
  category_id?: EntityId | null
  icon?: string | null
  summary?: string | null
  description?: string | null
  keywords?: string[]
  tags?: string[]
  component_key: string
  execution_mode: string
  status: string
  sort_order: number
  current_version_id?: EntityId | null
}

/** `ToolCreateRequest`. */
export interface ToolCreateRequest {
  code: string
  name: string
  slug: string
  component_key: string
  execution_mode: string
  category_id?: number | null
  icon?: string | null
  summary?: string | null
  description?: string | null
  keywords?: string[]
  tags?: string[]
  status?: string
  sort_order?: number
}

/** `ToolUpdateRequest`. */
export interface ToolUpdateRequest {
  code?: string | null
  name?: string | null
  slug?: string | null
  component_key?: string | null
  execution_mode?: string | null
  category_id?: number | null
  icon?: string | null
  summary?: string | null
  description?: string | null
  keywords?: string[] | null
  tags?: string[] | null
  status?: string | null
  sort_order?: number | null
}

/** `ToolStatusRequest`. */
export interface ToolStatusRequest {
  status: string
}

/** `PopularToolResponse`. */
export interface PopularTool {
  tool_id: EntityId
  tool_name?: string | null
  tool_slug?: string | null
  usage_count: number
  unique_user_count: number
  rank_no?: number | null
  score?: number | null
}

/** `RecentToolResponse`. */
export interface RecentTool {
  tool_id: EntityId
  tool_name?: string | null
  tool_slug?: string | null
  last_used_at: IsoDateTime
  use_count: number
}

// ---------------------------------------------------------------------------
// Access policy
// ---------------------------------------------------------------------------

/** `ToolAccessResponse`. */
export interface ToolAccess {
  tool_id: EntityId
  subject_type: string
  enabled: boolean
  daily_limit?: number | null
  used_today?: number
  remaining?: number | null
  rate_limit_per_minute?: number | null
  concurrency_limit?: number | null
}

/** `ToolUsageAdminResponse` — `GET /admin/tools/usage`. */
export interface ToolUsageAdmin {
  tool_id: EntityId
  tool_name?: string | null
  tool_slug?: string | null
  total_count: number
  success_count: number
  failure_count: number
  unique_user_count: number
  unique_guest_count: number
  last_used_at?: IsoDateTime | null
}

/** `ToolUsagePointAdminResponse` — `GET /admin/tools/usage/daily`. */
export interface ToolUsagePointAdmin {
  stat_date: string
  total_count: number
  success_count: number
  failure_count: number
}

/** `ToolUsageTrendPointAdminResponse` — `GET /admin/tools/usage/trend`. */
export interface ToolUsageTrendPointAdmin {
  stat_date: string
  total_count: number
  success_count: number
  failure_count: number
}

/** `ToolUsageOverviewAdminResponse` — `GET /admin/tools/usage/overview`. */
export interface ToolUsageOverviewAdmin {
  start_date: string
  end_date: string
  total_count: number
  success_count: number
  failure_count: number
  /** Percentage in `[0, 100]`. */
  success_rate: number
  unique_user_count: number
  unique_guest_count: number
  active_tool_count: number
  last_used_at?: IsoDateTime | null
}

/** `ToolVisibilityResponse` — who may use one tool. */
export interface ToolVisibility {
  tool_id: EntityId
  tool_code: string
  tool_name: string
  tool_slug: string
  status: string
  visibility: string
  guest_enabled: boolean
  user_enabled: boolean
  configured: boolean
}

/** `ToolVisibilityRequest`. */
export interface ToolVisibilityRequest {
  visibility: string
}

/** `AccessPolicyRequest`. */
export interface AccessPolicyRequest {
  subject_type: string
  enabled?: boolean
  daily_limit?: number | null
  rate_limit_per_minute?: number | null
  concurrency_limit?: number | null
}

/** `AccessPolicyAdminResponse`. */
export interface AdminAccessPolicy {
  id: EntityId
  tool_id?: EntityId | null
  tool_name?: string | null
  subject_type: string
  enabled: boolean
  daily_limit?: number | null
  rate_limit_per_minute?: number | null
  concurrency_limit?: number | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

// ---------------------------------------------------------------------------
// Execution
// ---------------------------------------------------------------------------

/** `ToolExecuteRequest`. */
export interface ToolExecuteRequest {
  inputs?: Record<string, unknown>
  anonymous_id?: string | null
  idempotency_key?: string | null
}

/** `ToolExecuteResponse`. */
export interface ToolExecuteResult {
  tool_id: EntityId
  usage_event_id?: string | null
  job_id?: string | null
  success: boolean
  output?: unknown
  duration_ms: number
  error_code?: string | null
  error_message?: string | null
  execution_mode: string
}

// ---------------------------------------------------------------------------
// Usage and statistics
// ---------------------------------------------------------------------------

/** `ToolUsageDailyResponse`. */
export interface ToolUsageDaily {
  id: EntityId
  stat_date: string
  tool_id?: EntityId | null
  total_count: number
  success_count: number
  failure_count: number
  guest_count: number
  user_count: number
  unique_user_count: number
  unique_guest_count: number
  avg_duration_ms?: number | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `ToolUsageResponse`. */
export interface ToolUsageRow {
  tool_id?: EntityId | null
  tool_name?: string | null
  tool_slug?: string | null
  view_count: number
  start_count: number
  execute_count: number
  success_count: number
  failure_count: number
  unique_user_count: number
}

/** `ToolUsageSummary`. */
export interface ToolUsageSummary {
  tool_id?: EntityId | null
  period_start: string
  period_end: string
  total_executions: number
  success_count: number
  failure_count: number
  unique_users: number
  avg_duration_ms?: number | null
}

/** `ToolPopularityDailyResponse`. */
export interface ToolPopularityDaily {
  id: EntityId
  stat_date: string
  window_days: number
  tool_id?: EntityId | null
  usage_count: number
  unique_user_count: number
  rank_no?: number | null
  score?: number | null
  created_at: IsoDateTime
}

/** `ToolRecentUsageResponse`. */
export interface ToolRecentUsage {
  id: EntityId
  user_id?: EntityId | null
  tool_id?: EntityId | null
  last_used_at: IsoDateTime
  use_count: number
}

/** `StatisticsRefreshRequest` / `PopularityRefreshRequest`. */
export interface RefreshRequest {
  stat_date: string
  window_days?: number
}

/** `StatisticsRefreshResponse` / `PopularityRefreshResponse`. */
export interface RefreshResult {
  stat_date: string
  window_days: number
  refreshed: number
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

/** `ToolJobResponse`. */
export interface ToolJob {
  id: EntityId
  job_code: string
  job_name: string
  job_type: string
  status: string
  priority: number
  attempt_count: number
  max_attempts: number
  available_at: IsoDateTime
  started_at?: IsoDateTime | null
  finished_at?: IsoDateTime | null
  last_error?: string | null
  trace_id?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
  payload?: Record<string, unknown> | null
}

/** `ToolJobListResponse`. */
export interface ToolJobList {
  items?: ToolJob[]
  total?: number
  page?: number
  page_size?: number
}
