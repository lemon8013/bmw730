/**
 * Analytics payloads, matching the schemas under `app/analytics` and
 * `app/admin/analytics/schema.py`.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

/** `AnalyticsOverviewResponse` (admin dashboard). */
export interface AnalyticsOverview {
  start: string
  end: string
  event_total: number
  event_unique_users: number
  event_unique_anonymous: number
  tool_views: number
  tool_starts: number
  tool_executions: number
  tool_success: number
  tool_failure: number
  tool_unique_users: number
  active_user_days: number
  user_event_total: number
  page_views: number
}

/** `OverviewResponse` (`/analytics/overview`). */
export interface OverviewResponse {
  pv: number
  uv: number
  active_users: number
  tool_top: ToolRankingItem[]
  generated_at: IsoDateTime
}

/** `ToolRankingItem`. */
export interface ToolRankingItem {
  tool_id?: EntityId | null
  execute_count: number
  success_count: number
  failure_count: number
  unique_user_count: number
}

/** `TrendPoint`. */
export interface TrendPoint {
  stat_date: string
  pv: number
  uv: number
}

/** `TrendResponse`. */
export interface TrendResponse {
  start_date: string
  end_date: string
  points: TrendPoint[]
}

/** `FunnelStepSummary`. */
export interface FunnelStepSummary {
  step_no: number
  step_code: string
  event_code: string
  enabled: boolean
  event_count: number
}

/** `FunnelSummaryItem`. */
export interface FunnelSummaryItem {
  funnel_code: string
  funnel_name: string
  first_step_count: number
  steps: FunnelStepSummary[]
}

/** `FunnelResponse`. */
export interface Funnel {
  id: EntityId
  funnel_code: string
  funnel_name: string
  step_no: number
  step_code: string
  event_code: string
  enabled: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `FunnelCreateRequest`. */
export interface FunnelCreateRequest {
  funnel_code: string
  funnel_name: string
  step_no: number
  step_code: string
  event_code: string
  enabled?: boolean
}

/** `FunnelUpdateRequest`. */
export interface FunnelUpdateRequest {
  funnel_name?: string | null
  step_no?: number | null
  step_code?: string | null
  event_code?: string | null
  enabled?: boolean | null
}

/** `BehaviorEventResponse`. */
export interface BehaviorEvent {
  id: EntityId
  event_id: string
  event_code: string
  event_name?: string | null
  anonymous_id_hash?: string | null
  user_id?: EntityId | null
  session_id?: string | null
  platform?: string | null
  device_type?: string | null
  os?: string | null
  browser?: string | null
  app_code?: string | null
  app_version?: string | null
  page_code?: string | null
  page_url?: string | null
  referrer?: string | null
  module?: string | null
  resource_type?: string | null
  resource_id?: string | null
  properties?: Record<string, unknown> | null
  trace_id?: string | null
  request_id?: string | null
  occurred_at: IsoDateTime
  received_at: IsoDateTime
}

/** `BehaviorEventWriteRequest`. */
export interface BehaviorEventWriteRequest {
  event_id?: string | null
  event_code: string
  event_name?: string | null
  anonymous_id_hash?: string | null
  user_id?: EntityId | null
  session_id?: string | null
  platform?: string | null
  device_type?: string | null
  os?: string | null
  browser?: string | null
  app_code?: string | null
  app_version?: string | null
  page_code?: string | null
  page_url?: string | null
  referrer?: string | null
  module?: string | null
  resource_type?: string | null
  resource_id?: string | null
  properties?: Record<string, unknown> | null
  trace_id?: string | null
  request_id?: string | null
  occurred_at?: string | null
}

/** `IdentityMergeRequest`. */
export interface IdentityMergeRequest {
  anonymous_id_hash: string
  user_id?: EntityId | null
  first_seen_at?: string | null
}

/** `IdentityMergeResponse`. */
export interface IdentityMerge {
  id: EntityId
  anonymous_id_hash: string
  user_id?: EntityId | null
  first_seen_at?: string | null
  merged_at: IsoDateTime
}

/** `app__admin__analytics__schema__EventDailyResponse`. */
export interface EventDaily {
  id: EntityId
  stat_date: string
  event_code: string
  total_count: number
  unique_user_count: number
  unique_anonymous_count: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `PageDailyResponse`. */
export interface PageDaily {
  id: EntityId
  stat_date: string
  page_code: string
  view_count: number
  unique_user_count: number
  unique_anonymous_count: number
  avg_duration_ms?: number | null
}

/** `UserDailyResponse`. */
export interface UserDaily {
  id: EntityId
  stat_date: string
  user_id?: EntityId | null
  anonymous_id_hash?: string | null
  event_count: number
  active: boolean
  first_event_at?: IsoDateTime | null
  last_event_at?: IsoDateTime | null
}

/** `ToolDailyResponse`. */
export interface ToolDaily {
  id: EntityId
  stat_date: string
  tool_id?: EntityId | null
  view_count: number
  start_count: number
  execute_count: number
  success_count: number
  failure_count: number
  copy_count: number
  download_count: number
  unique_user_count: number
}

/** `SearchDailyResponse`. */
export interface SearchDaily {
  id: EntityId
  stat_date: string
  search_type: string
  keyword_hash: string
  search_count: number
  result_click_count: number
}

/** `ToolUsageResponse` used by the admin tool-usage table. */
export interface ToolUsageDailyRow {
  stat_date: string
  tool_id?: EntityId | null
  total_count: number
  success_count: number
  failure_count: number
  guest_count: number
  user_count: number
  unique_user_count: number
}

/** `RecomputeRequest`. */
export interface RecomputeRequest {
  start_date?: string | null
  end_date?: string | null
}

/** `RecomputeResponse`. */
export interface RecomputeResult {
  start: string
  end: string
  recomputed_rows: number
}

/** Query parameters of `GET /analytics/events`. */
export interface EventQuery {
  event_code?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

/** Query parameters of `GET /analytics/identity-merges`. */
export interface IdentityMergeQuery {
  anonymous_id_hash?: string
  user_id?: EntityId
  page?: number
  page_size?: number
}

/** Query parameters shared by the daily statistics endpoints. */
export interface DailyQuery {
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}
