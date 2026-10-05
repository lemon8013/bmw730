/** Analytics: admin dashboard plus the behaviour analytics module. */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  AnalyticsOverview,
  BehaviorEvent,
  DailyQuery,
  EventDaily,
  EventQuery,
  Funnel,
  FunnelCreateRequest,
  FunnelSummaryItem,
  FunnelUpdateRequest,
  IdentityMerge,
  IdentityMergeQuery,
  OverviewResponse,
  PageDaily,
  RecomputeRequest,
  RecomputeResult,
  SearchDaily,
  ToolDaily,
  ToolRankingItem,
  TrendResponse,
  UserDaily,
} from '@/types/analytics'

// --- admin dashboard -------------------------------------------------------

/** `GET /admin/analytics/overview` */
export function getAdminOverview(start?: string, end?: string): Promise<AnalyticsOverview> {
  return get<AnalyticsOverview>('/admin/analytics/overview', { params: { start, end } })
}

/** `GET /admin/analytics/events/daily` */
export function getAdminEventsDaily(query: {
  event_code?: string
  start?: string
  end?: string
  page?: number
  page_size?: number
} = {}): Promise<Page<EventDaily>> {
  return get<Page<EventDaily>>('/admin/analytics/events/daily', { params: query })
}

/** `GET /admin/analytics/tool-usage` */
export function getAdminToolUsage(query: {
  start?: string
  end?: string
  page?: number
  page_size?: number
} = {}): Promise<Page<Record<string, unknown>>> {
  return get<Page<Record<string, unknown>>>('/admin/analytics/tool-usage', { params: query })
}

/** `POST /admin/analytics/recompute` */
export function adminRecompute(start?: string, end?: string): Promise<RecomputeResult> {
  return post<RecomputeResult>('/admin/analytics/recompute', undefined, {
    params: { start, end },
  })
}

// --- behaviour analytics ---------------------------------------------------

/** `GET /analytics/events` */
export function queryEvents(query: EventQuery = {}): Promise<Page<BehaviorEvent>> {
  return get<Page<BehaviorEvent>>('/analytics/events', { params: query })
}

/** `GET /analytics/identity-merges` */
export function queryIdentityMerges(
  query: IdentityMergeQuery = {},
): Promise<Page<IdentityMerge>> {
  return get<Page<IdentityMerge>>('/analytics/identity-merges', { params: query })
}

/** `GET /analytics/overview` */
export function getOverview(
  startDate?: string,
  endDate?: string,
  limit = 10,
): Promise<OverviewResponse> {
  return get<OverviewResponse>('/analytics/overview', {
    params: { start_date: startDate, end_date: endDate, limit },
  })
}

/** `GET /analytics/trends` */
export function getTrends(startDate?: string, endDate?: string): Promise<TrendResponse> {
  return get<TrendResponse>('/analytics/trends', {
    params: { start_date: startDate, end_date: endDate },
  })
}

/** `GET /analytics/tool-rankings` */
export function getToolRankings(
  startDate?: string,
  endDate?: string,
  limit = 10,
): Promise<ToolRankingItem[]> {
  return get<ToolRankingItem[]>('/analytics/tool-rankings', {
    params: { start_date: startDate, end_date: endDate, limit },
  })
}

/** `GET /analytics/funnel-summary` */
export function getFunnelSummary(
  startDate?: string,
  endDate?: string,
): Promise<FunnelSummaryItem[]> {
  return get<FunnelSummaryItem[]>('/analytics/funnel-summary', {
    params: { start_date: startDate, end_date: endDate },
  })
}

// --- daily statistics ------------------------------------------------------

/** `GET /analytics/events/daily` */
export function getEventsDaily(
  query: DailyQuery & { event_code?: string } = {},
): Promise<Page<EventDaily>> {
  return get<Page<EventDaily>>('/analytics/events/daily', { params: query })
}

/** `GET /analytics/users/daily` */
export function getUsersDaily(query: DailyQuery & { user_id?: string } = {}): Promise<Page<UserDaily>> {
  return get<Page<UserDaily>>('/analytics/users/daily', { params: query })
}

/** `GET /analytics/pages/daily` */
export function getPagesDaily(
  query: DailyQuery & { page_code?: string } = {},
): Promise<Page<PageDaily>> {
  return get<Page<PageDaily>>('/analytics/pages/daily', { params: query })
}

/** `GET /analytics/tools/daily` */
export function getToolsDaily(query: DailyQuery & { tool_id?: string } = {}): Promise<Page<ToolDaily>> {
  return get<Page<ToolDaily>>('/analytics/tools/daily', { params: query })
}

/** `GET /analytics/searches/daily` */
export function getSearchesDaily(
  query: DailyQuery & { search_type?: string } = {},
): Promise<Page<SearchDaily>> {
  return get<Page<SearchDaily>>('/analytics/searches/daily', { params: query })
}

/** `POST /analytics/recompute` */
export function recompute(payload: RecomputeRequest): Promise<Record<string, number>> {
  return post<Record<string, number>>('/analytics/recompute', payload)
}

// --- funnels ---------------------------------------------------------------

/** `GET /analytics/funnels` */
export function listFunnels(enabledOnly = false): Promise<Funnel[]> {
  return get<Funnel[]>('/analytics/funnels', { params: { enabled_only: enabledOnly } })
}

/** `POST /analytics/funnels` */
export function createFunnel(payload: FunnelCreateRequest): Promise<Funnel> {
  return post<Funnel>('/analytics/funnels', payload, {
    vctn: { idempotencyKey: `create-funnel:${payload.funnel_code}:${payload.step_no}` },
  })
}

/** `PUT /analytics/funnels/{funnel_id}` */
export function updateFunnel(funnelId: string, payload: FunnelUpdateRequest): Promise<Funnel> {
  return put<Funnel>(`/analytics/funnels/${funnelId}`, payload)
}

/** `DELETE /analytics/funnels/{funnel_id}` */
export function deleteFunnel(funnelId: string): Promise<boolean> {
  return del<boolean>(`/analytics/funnels/${funnelId}`)
}
