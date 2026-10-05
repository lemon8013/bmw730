/** Cosmetic catalogue (`app/platform/cosmetics`). */

import { get } from '@/api/client'
import type { Cosmetic } from '@/types/growth'

/**
 * `GET /cosmetics`
 *
 * `/cosmetics/me` is deliberately not wrapped: it resolves identity from the
 * signed-in business user, which an operator session does not have.
 */
export function listCosmetics(): Promise<Cosmetic[]> {
  return get<Cosmetic[]>('/cosmetics')
}
