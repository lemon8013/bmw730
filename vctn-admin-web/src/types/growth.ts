/**
 * Growth / points / levels / cosmetics / tasks / achievements payloads.
 *
 * These mirror the read endpoints the backend actually exposes. No write
 * endpoint is declared here that the backend does not implement.
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
