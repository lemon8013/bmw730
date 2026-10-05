/** Level reads (`app/platform/levels`). */

import { get } from '@/api/client'
import type { UserLevel } from '@/types/growth'

/**
 * `GET /levels`
 *
 * `/levels/me` and `/levels/me/history` are deliberately not wrapped: they
 * resolve identity from the signed-in business user, which an operator session
 * does not have.
 */
export function listLevels(): Promise<UserLevel[]> {
  return get<UserLevel[]>('/levels')
}
