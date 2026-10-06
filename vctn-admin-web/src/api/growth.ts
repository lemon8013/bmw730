/**
 * Administrator growth API (`app/admin/growth`).
 *
 * Why this exists alongside `api/points.ts` and friends: every platform
 * gamification endpoint is `/me`-shaped and answers 401 for an operator
 * session. These calls address the same data by explicit user id and add the
 * catalogue CRUD the console needs.
 */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  BizUserBrief,
  GrowthAccountAdmin,
  GrowthAdjustPayload,
  GrowthAdjustResult,
  GrowthOverviewAdmin,
  GrowthRule,
  GrowthRuleCreatePayload,
  GrowthRuleUpdatePayload,
  GrowthTransaction,
  LevelCreatePayload,
  LevelHistoryAdmin,
  LevelUpdatePayload,
  PointAccountAdmin,
  PointAdjustPayload,
  PointAdjustResult,
  PointRule,
  PointRuleCreatePayload,
  PointRuleUpdatePayload,
  PointTransaction,
  Task,
  TaskCreatePayload,
  TaskUpdatePayload,
  UserAchievementAdmin,
  UserCosmeticAdmin,
  UserEquipmentAdmin,
  UserGrowthSummaryAdmin,
  UserLevel,
  UserLevelAdmin,
  UserTaskAdmin,
} from '@/types/growth'

// ---------------------------------------------------------------------------
// Business users
// ---------------------------------------------------------------------------

/** `GET /admin/biz-users` */
export function listBizUsers(params: {
  keyword?: string | null
  status?: string | null
  page?: number
  page_size?: number
}): Promise<Page<BizUserBrief>> {
  return get<Page<BizUserBrief>>('/admin/biz-users', { params })
}

// ---------------------------------------------------------------------------
// Growth
// ---------------------------------------------------------------------------

/** `GET /admin/growth/overview` */
export function getGrowthOverview(): Promise<GrowthOverviewAdmin> {
  return get<GrowthOverviewAdmin>('/admin/growth/overview')
}

/** `GET /admin/growth/rules` */
export function listAdminGrowthRules(
  includeDisabled = true,
): Promise<GrowthRule[]> {
  return get<GrowthRule[]>('/admin/growth/rules', {
    params: { include_disabled: includeDisabled },
  })
}

/** `POST /admin/growth/rules` */
export function createGrowthRule(
  payload: GrowthRuleCreatePayload,
): Promise<GrowthRule> {
  return post<GrowthRule>('/admin/growth/rules', payload)
}

/** `PUT /admin/growth/rules/{id}` */
export function updateGrowthRule(
  ruleId: string,
  payload: GrowthRuleUpdatePayload,
): Promise<GrowthRule> {
  return put<GrowthRule>(`/admin/growth/rules/${ruleId}`, payload)
}

/** `DELETE /admin/growth/rules/{id}` */
export function deleteGrowthRule(ruleId: string): Promise<unknown> {
  return del<unknown>(`/admin/growth/rules/${ruleId}`)
}

/** `GET /admin/users/{id}/growth` */
export function getUserGrowth(userId: string): Promise<GrowthAccountAdmin> {
  return get<GrowthAccountAdmin>(`/admin/users/${userId}/growth`)
}

/** `GET /admin/users/{id}/growth/transactions` */
export function getUserGrowthTransactions(
  userId: string,
  params: { page?: number; page_size?: number },
): Promise<Page<GrowthTransaction>> {
  return get<Page<GrowthTransaction>>(`/admin/users/${userId}/growth/transactions`, {
    params,
  })
}

/** `POST /admin/users/{id}/growth/adjust` */
export function adjustUserGrowth(
  userId: string,
  payload: GrowthAdjustPayload,
): Promise<GrowthAdjustResult> {
  return post<GrowthAdjustResult>(`/admin/users/${userId}/growth/adjust`, payload)
}

// ---------------------------------------------------------------------------
// Points
// ---------------------------------------------------------------------------

/** `GET /admin/points/rules` */
export function listAdminPointRules(includeDisabled = true): Promise<PointRule[]> {
  return get<PointRule[]>('/admin/points/rules', {
    params: { include_disabled: includeDisabled },
  })
}

/** `POST /admin/points/rules` */
export function createPointRule(payload: PointRuleCreatePayload): Promise<PointRule> {
  return post<PointRule>('/admin/points/rules', payload)
}

/** `PUT /admin/points/rules/{id}` */
export function updatePointRule(
  ruleId: string,
  payload: PointRuleUpdatePayload,
): Promise<PointRule> {
  return put<PointRule>(`/admin/points/rules/${ruleId}`, payload)
}

/** `DELETE /admin/points/rules/{id}` */
export function deletePointRule(ruleId: string): Promise<unknown> {
  return del<unknown>(`/admin/points/rules/${ruleId}`)
}

/** `GET /admin/users/{id}/points` */
export function getUserPoints(userId: string): Promise<PointAccountAdmin> {
  return get<PointAccountAdmin>(`/admin/users/${userId}/points`)
}

/** `GET /admin/users/{id}/points/transactions` */
export function getUserPointTransactions(
  userId: string,
  params: { page?: number; page_size?: number },
): Promise<Page<PointTransaction>> {
  return get<Page<PointTransaction>>(`/admin/users/${userId}/points/transactions`, {
    params,
  })
}

/** `POST /admin/users/{id}/points/adjust` */
export function adjustUserPoints(
  userId: string,
  payload: PointAdjustPayload,
): Promise<PointAdjustResult> {
  return post<PointAdjustResult>(`/admin/users/${userId}/points/adjust`, payload)
}

// ---------------------------------------------------------------------------
// Levels
// ---------------------------------------------------------------------------

/** `GET /admin/levels` */
export function listAdminLevels(includeDisabled = true): Promise<UserLevel[]> {
  return get<UserLevel[]>('/admin/levels', {
    params: { include_disabled: includeDisabled },
  })
}

/** `POST /admin/levels` */
export function createLevel(payload: LevelCreatePayload): Promise<UserLevel> {
  return post<UserLevel>('/admin/levels', payload)
}

/** `PUT /admin/levels/{id}` */
export function updateLevel(
  levelId: string,
  payload: LevelUpdatePayload,
): Promise<UserLevel> {
  return put<UserLevel>(`/admin/levels/${levelId}`, payload)
}

/**
 * `DELETE /admin/levels/{id}`
 *
 * Retiring is always soft: `biz_user_growth_account` holds a foreign key to the
 * level, so a physical delete is not possible once a user reached it.
 */
export function deleteLevel(levelId: string): Promise<unknown> {
  return del<unknown>(`/admin/levels/${levelId}`)
}

/** `GET /admin/users/{id}/levels` */
export function getUserLevel(userId: string): Promise<UserLevelAdmin> {
  return get<UserLevelAdmin>(`/admin/users/${userId}/levels`)
}

/** `GET /admin/users/{id}/levels/history` */
export function getUserLevelHistory(
  userId: string,
  params: { page?: number; page_size?: number },
): Promise<Page<LevelHistoryAdmin>> {
  return get<Page<LevelHistoryAdmin>>(`/admin/users/${userId}/levels/history`, { params })
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

/** `GET /admin/tasks` */
export function listAdminTasks(includeDisabled = true): Promise<Task[]> {
  return get<Task[]>('/admin/tasks', { params: { include_disabled: includeDisabled } })
}

/** `POST /admin/tasks` */
export function createTask(payload: TaskCreatePayload): Promise<Task> {
  return post<Task>('/admin/tasks', payload)
}

/** `PUT /admin/tasks/{id}` */
export function updateTask(taskId: string, payload: TaskUpdatePayload): Promise<Task> {
  return put<Task>(`/admin/tasks/${taskId}`, payload)
}

/** `DELETE /admin/tasks/{id}` — always a soft delete. */
export function deleteTask(taskId: string): Promise<unknown> {
  return del<unknown>(`/admin/tasks/${taskId}`)
}

/** `GET /admin/users/{id}/tasks` */
export function getUserTasks(userId: string): Promise<UserTaskAdmin[]> {
  return get<UserTaskAdmin[]>(`/admin/users/${userId}/tasks`)
}

// ---------------------------------------------------------------------------
// Achievements / cosmetics
// ---------------------------------------------------------------------------

/** `GET /admin/users/{id}/achievements` */
export function getUserAchievements(userId: string): Promise<UserAchievementAdmin[]> {
  return get<UserAchievementAdmin[]>(`/admin/users/${userId}/achievements`)
}

/** `GET /admin/users/{id}/cosmetics` */
export function getUserCosmetics(userId: string): Promise<UserCosmeticAdmin[]> {
  return get<UserCosmeticAdmin[]>(`/admin/users/${userId}/cosmetics`)
}

/** `GET /admin/users/{id}/cosmetics/equipment` */
export function getUserEquipment(userId: string): Promise<UserEquipmentAdmin> {
  return get<UserEquipmentAdmin>(`/admin/users/${userId}/cosmetics/equipment`)
}

// ---------------------------------------------------------------------------
// Cross-module summary
// ---------------------------------------------------------------------------

/** `GET /admin/users/{id}/summary` */
export function getUserGrowthSummary(userId: string): Promise<UserGrowthSummaryAdmin> {
  return get<UserGrowthSummaryAdmin>(`/admin/users/${userId}/summary`)
}
