/**
 * Growth / points / levels / cosmetics / tasks / achievements payloads.
 *
 * These mirror the endpoints the backend actually exposes. Since the platform
 * side is `/me`-shaped (identity comes from the signed-in **business user**, so
 * an operator session gets 401), the console reads everything through the
 * `/admin/...` surface declared at the bottom of this file.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

// ---------------------------------------------------------------------------
// Growth
// ---------------------------------------------------------------------------

/** `GrowthAccountResponse` (`/growth/me`). */
export interface GrowthAccount {
  user_id: EntityId
  total_growth_points: number
  current_level_id?: EntityId | null
  current_level_name?: string | null
  current_level_no?: number | null
  next_level_id?: EntityId | null
  next_level_name?: string | null
  next_level_points_required?: number | null
  version: number
  updated_at: IsoDateTime
}

/** `GrowthTransactionResponse`. */
export interface GrowthTransaction {
  id: EntityId
  user_id: EntityId
  event_id?: string | null
  delta_points: number
  balance_after: number
  transaction_type: string
  reason?: string | null
  created_at: IsoDateTime
}

// ---------------------------------------------------------------------------
// Points
// ---------------------------------------------------------------------------

/** `PointAccountResponse` (`/points/me`). */
export interface PointAccount {
  user_id: EntityId
  balance: number
  total_earned: number
  total_spent: number
  version: number
  updated_at: IsoDateTime
}

/** `PointTransactionResponse`. */
export interface PointTransaction {
  id: EntityId
  user_id: EntityId
  event_id?: string | null
  delta_points: number
  balance_after: number
  transaction_type: string
  source_type?: string | null
  source_id?: string | null
  reason?: string | null
  created_at: IsoDateTime
}

/** `PointRuleResponse` (`/point-rules/public`). */
export interface PointRule {
  id: EntityId
  rule_code: string
  rule_name: string
  event_code: string
  points: number
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled: boolean
  conditions?: Record<string, unknown> | null
  description?: string | null
}

// ---------------------------------------------------------------------------
// Levels
// ---------------------------------------------------------------------------

/** `LevelResponse`. */
export interface UserLevel {
  id: EntityId
  level_code: string
  level_name: string
  level_no: number
  min_growth_points: number
  max_growth_points?: number | null
  icon_url?: string | null
  description?: string | null
  status: string
  sort_order: number
}

/** `LevelBenefitResponse`. */
export interface LevelBenefit {
  id: EntityId
  level_id: EntityId
  benefit_type: string
  benefit_code: string
  benefit_value?: Record<string, unknown> | null
  enabled: boolean
}

/** `MyLevelResponse` (`/levels/me`). */
export interface MyLevel {
  user_id: EntityId
  total_growth_points: number
  current_level?: UserLevel | null
  next_level?: UserLevel | null
  points_to_next_level?: number | null
  benefits?: LevelBenefit[]
}

/** `LevelHistoryResponse`. */
export interface LevelHistory {
  id: EntityId
  user_id: EntityId
  from_level_id?: EntityId | null
  to_level_id?: EntityId | null
  growth_points: number
  reason?: string | null
  created_at: IsoDateTime
}

// ---------------------------------------------------------------------------
// Cosmetics
// ---------------------------------------------------------------------------

/** `CosmeticResponse`. */
export interface Cosmetic {
  id: EntityId
  cosmetic_code: string
  cosmetic_name: string
  cosmetic_type: string
  asset_url?: string | null
  metadata?: Record<string, unknown> | null
  status: string
  sort_order: number
  owned?: boolean
}

/** `UserCosmeticResponse`. */
export interface UserCosmetic {
  id: EntityId
  user_id: EntityId
  cosmetic_id: EntityId
  cosmetic_name?: string | null
  cosmetic_type?: string | null
  obtained_at: IsoDateTime
  source_type?: string | null
  source_id?: string | null
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

/** `TaskResponse`. */
export interface Task {
  id: EntityId
  task_code: string
  task_name: string
  task_type: string
  conditions?: Record<string, unknown> | null
  reward?: Record<string, unknown> | null
  start_at?: IsoDateTime | null
  end_at?: IsoDateTime | null
  repeatable: boolean
  status: string
}

/** `UserTaskResponse`. */
export interface UserTask {
  id: EntityId
  user_id: EntityId
  task_id: EntityId
  task_name?: string | null
  progress?: Record<string, unknown> | null
  status: string
  completed_at?: IsoDateTime | null
  reward_claimed?: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

// ---------------------------------------------------------------------------
// Achievements
// ---------------------------------------------------------------------------

/** `AchievementResponse`. */
export interface Achievement {
  id: EntityId
  achievement_code: string
  achievement_name: string
  conditions?: Record<string, unknown> | null
  reward?: Record<string, unknown> | null
  status: string
}

/** `UserAchievementResponse`. */
export interface UserAchievement {
  id: EntityId
  user_id: EntityId
  achievement_id: EntityId
  achievement_name?: string | null
  achieved_at: IsoDateTime
}

// ---------------------------------------------------------------------------
// Administrator surface (`/api/v1/admin/...`)
//
// Every platform gamification endpoint resolves identity from the signed-in
// business user. The console signs in as an operator, so it needs these
// variants that address data by an explicit user id.
// ---------------------------------------------------------------------------

/** `BizUserBriefResponse` — a platform business user. */
export interface BizUserBrief {
  user_id: EntityId
  username?: string | null
  nickname?: string | null
  email?: string | null
  status: string
  registered_at?: IsoDateTime | null
  last_login_at?: IsoDateTime | null
}

/** `GrowthAccountAdminResponse`. */
export interface GrowthAccountAdmin {
  user_id: EntityId
  username?: string | null
  nickname?: string | null
  total_growth_points: number
  current_level_id?: EntityId | null
  current_level_name?: string | null
  current_level_no?: number | null
  next_level_id?: EntityId | null
  next_level_name?: string | null
  next_level_points_required?: number | null
  version: number
  updated_at: IsoDateTime
}

/** `GrowthAdjustRequest`. */
export interface GrowthAdjustPayload {
  delta_points: number
  reason?: string
  idempotency_key?: string | null
}

/** `GrowthAdjustResponse`. */
export interface GrowthAdjustResult {
  user_id: EntityId
  delta_points: number
  total_growth_points: number
  level_changed: boolean
  transaction_id?: EntityId | null
}

/** `GrowthRuleCreateRequest`. */
export interface GrowthRuleCreatePayload {
  rule_code: string
  rule_name: string
  event_code: string
  growth_points: number
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled?: boolean
  conditions?: Record<string, unknown> | null
  description?: string | null
}

/** `GrowthRuleUpdateRequest`. */
export interface GrowthRuleUpdatePayload {
  rule_name?: string | null
  growth_points?: number | null
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled?: boolean | null
  conditions?: Record<string, unknown> | null
  description?: string | null
}

/** `GrowthRuleResponse` — also used by the admin rules endpoints. */
export interface GrowthRule {
  id: EntityId
  rule_code: string
  rule_name: string
  event_code: string
  growth_points: number
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled: boolean
  conditions?: Record<string, unknown> | null
  description?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `PointAccountAdminResponse`. */
export interface PointAccountAdmin {
  user_id: EntityId
  username?: string | null
  nickname?: string | null
  balance: number
  total_earned: number
  total_spent: number
  version: number
  updated_at: IsoDateTime
}

/** `PointAdjustRequest`. */
export interface PointAdjustPayload {
  delta_points: number
  reason?: string
}

/** `PointAdjustResponse`. */
export interface PointAdjustResult {
  user_id: EntityId
  delta_points: number
  balance: number
  transaction_id: EntityId
}

/** `PointRuleCreateRequest`. */
export interface PointRuleCreatePayload {
  rule_code: string
  rule_name: string
  event_code: string
  points: number
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled?: boolean
  conditions?: Record<string, unknown> | null
  description?: string | null
}

/** `PointRuleUpdateRequest`. */
export interface PointRuleUpdatePayload {
  rule_name?: string | null
  points?: number | null
  daily_limit?: number | null
  cooldown_seconds?: number | null
  enabled?: boolean | null
  conditions?: Record<string, unknown> | null
  description?: string | null
}

/** `LevelCreateRequest`. */
export interface LevelCreatePayload {
  level_code: string
  level_name: string
  level_no: number
  min_growth_points: number
  max_growth_points?: number | null
  icon_url?: string | null
  description?: string | null
  status?: string
  sort_order?: number
}

/** `LevelUpdateRequest`. */
export interface LevelUpdatePayload {
  level_name?: string | null
  level_no?: number | null
  min_growth_points?: number | null
  max_growth_points?: number | null
  icon_url?: string | null
  description?: string | null
  status?: string | null
  sort_order?: number | null
}

/** `UserLevelAdminResponse`. */
export interface UserLevelAdmin {
  user_id: EntityId
  username?: string | null
  nickname?: string | null
  total_growth_points: number
  current_level_id?: EntityId | null
  current_level_name?: string | null
  current_level_no?: number | null
  current_level_icon_url?: string | null
  next_level_id?: EntityId | null
  next_level_name?: string | null
  next_level_points_required?: number | null
  level_changed_count: number
}

/** `LevelHistoryAdminResponse`. */
export interface LevelHistoryAdmin {
  id: EntityId
  user_id: EntityId
  from_level_id?: EntityId | null
  from_level_name?: string | null
  to_level_id?: EntityId | null
  to_level_name?: string | null
  growth_points: number
  reason?: string | null
  created_at: IsoDateTime
}

/** `TaskCreateRequest`. */
export interface TaskCreatePayload {
  task_code: string
  task_name: string
  task_type: string
  conditions?: Record<string, unknown>
  reward?: Record<string, unknown> | null
  start_at?: IsoDateTime | null
  end_at?: IsoDateTime | null
  repeatable?: boolean
  status?: string
}

/** `TaskUpdateRequest`. */
export interface TaskUpdatePayload {
  task_name?: string | null
  task_type?: string | null
  conditions?: Record<string, unknown> | null
  reward?: Record<string, unknown> | null
  start_at?: IsoDateTime | null
  end_at?: IsoDateTime | null
  repeatable?: boolean | null
  status?: string | null
}

/** `UserTaskAdminResponse`. */
export interface UserTaskAdmin {
  id: EntityId
  user_id: EntityId
  task_id: EntityId
  task_code?: string | null
  task_name?: string | null
  task_type?: string | null
  target_count?: number | null
  current_count: number
  status: string
  completed_at?: IsoDateTime | null
  reward_claimed: boolean
  reward?: Record<string, unknown> | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `UserAchievementAdminResponse`. */
export interface UserAchievementAdmin {
  achievement_id: EntityId
  achievement_code: string
  achievement_name: string
  conditions?: Record<string, unknown> | null
  reward?: Record<string, unknown> | null
  status: string
  unlocked: boolean
  achieved_at?: IsoDateTime | null
}

/** `UserCosmeticAdminResponse`. */
export interface UserCosmeticAdmin {
  cosmetic_id: EntityId
  cosmetic_code: string
  cosmetic_name: string
  cosmetic_type: string
  asset_url?: string | null
  sort_order: number
  owned: boolean
  obtained_at?: IsoDateTime | null
  source_type?: string | null
}

/** `UserEquipmentAdminResponse`. */
export interface UserEquipmentAdmin {
  user_id: EntityId
  [slot: string]: EntityId | string | null | undefined
}

/** `UserGrowthSummaryAdminResponse`. */
export interface UserGrowthSummaryAdmin {
  user: BizUserBrief
  growth?: GrowthAccountAdmin | null
  points?: PointAccountAdmin | null
  level?: UserLevelAdmin | null
  task_total: number
  task_completed: number
  task_reward_claimed: number
  achievement_total: number
  achievement_unlocked: number
  cosmetic_total: number
  cosmetic_owned: number
}

/** `GrowthOverviewAdminResponse`. */
export interface GrowthOverviewAdmin {
  biz_user_count: number
  growth_account_count: number
  total_growth_points: number
  point_account_count: number
  total_point_balance: number
  user_task_count: number
  user_task_completed: number
  user_task_reward_claimed: number
  user_achievement_count: number
  growth_rule_count: number
  growth_rule_enabled: number
  point_rule_count: number
  point_rule_enabled: number
  task_count: number
  achievement_count: number
  level_count: number
  cosmetic_count: number
}
