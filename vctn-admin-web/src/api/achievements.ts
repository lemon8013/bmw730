/** Achievement catalogue (`app/platform/growth`). */

import { get } from '@/api/client'
import type { Achievement } from '@/types/growth'

/**
 * `GET /achievements`
 *
 * `/achievements/me` is deliberately not wrapped: it resolves identity from the
 * signed-in business user, which an operator session does not have.
 */
export function listAchievements(): Promise<Achievement[]> {
  return get<Achievement[]>('/achievements')
}
