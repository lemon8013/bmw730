/** Point reads (`app/platform/points`). */

import { get } from '@/api/client'
import type { PointRule } from '@/types/growth'

/**
 * `GET /point-rules/public`
 *
 * The only point endpoint an operator session can read. `/points/me` and
 * `/points/me/transactions` resolve identity from the signed-in **business
 * user**, so the console omits them.
 */
export function listPointRules(): Promise<PointRule[]> {
  return get<PointRule[]>('/point-rules/public')
}
