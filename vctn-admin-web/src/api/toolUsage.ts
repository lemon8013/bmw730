/** Tool usage and statistics (`app/tools/usage`, `app/tools/statistics`). */

import { get, post } from '@/api/client'
import type {
  RefreshRequest,
  RefreshResult,
  ToolPopularityDaily,
  ToolRecentUsage,
  ToolUsageDaily,
  ToolUsageSummary,
} from '@/types/tools'

/** `GET /tools/usage/daily` */
export function getUsageDaily(
  toolId: string,
  start: string,
  end: string,
): Promise<ToolUsageDaily[]> {
  return get<ToolUsageDaily[]>('/tools/usage/daily', { params: { tool_id: toolId, start, end } })
}

/** `GET /tools/usage/summary` */
export function getUsageSummary(
  toolId: string,
  start: string,
  end: string,
): Promise<ToolUsageSummary> {
  return get<ToolUsageSummary>('/tools/usage/summary', {
    params: { tool_id: toolId, start, end },
  })
}

/** `GET /tools/usage/popularity` */
export function getUsagePopularity(
  statDate: string,
  windowDays = 7,
  limit = 20,
): Promise<ToolPopularityDaily[]> {
  return get<ToolPopularityDaily[]>('/tools/usage/popularity', {
    params: { stat_date: statDate, window_days: windowDays, limit },
  })
}

/** `GET /tools/usage/recent` */
export function getRecentUsage(userId?: string, limit = 20): Promise<ToolRecentUsage[]> {
  return get<ToolRecentUsage[]>('/tools/usage/recent', {
    params: userId ? { user_id: userId, limit } : { limit },
  })
}

/** `POST /tools/usage/refresh-popularity` */
export function refreshPopularity(payload: RefreshRequest): Promise<RefreshResult> {
  return post<RefreshResult>('/tools/usage/refresh-popularity', payload)
}

/** `GET /tools/statistics/usage-daily` */
export function getStatisticsUsageDaily(
  toolId: string,
  start: string,
  end: string,
): Promise<ToolUsageDaily[]> {
  return get<ToolUsageDaily[]>('/tools/statistics/usage-daily', {
    params: { tool_id: toolId, start, end },
  })
}

/** `GET /tools/statistics/popularity` */
export function getStatisticsPopularity(
  statDate: string,
  windowDays = 7,
  limit = 20,
): Promise<ToolPopularityDaily[]> {
  return get<ToolPopularityDaily[]>('/tools/statistics/popularity', {
    params: { stat_date: statDate, window_days: windowDays, limit },
  })
}

/** `POST /tools/statistics/refresh` */
export function refreshStatistics(payload: RefreshRequest): Promise<RefreshResult> {
  return post<RefreshResult>('/tools/statistics/refresh', payload)
}
