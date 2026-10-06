/**
 * Business-user authentication types.
 *
 * Mirrors `app/platform/auth/schema.py`. The blog is readable anonymously;
 * signing in is what unlocks commenting, liking and authoring.
 */

import type { EntityId } from '@/types/api'

/** Issued credential pair. */
export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in: number
}

/** Registration payload. */
export interface RegisterRequest {
  username: string
  password: string
  nickname?: string | null
  email?: string | null
  phone?: string | null
}

/** Login payload — the backend accepts username, email or phone. */
export interface LoginRequest {
  identity: string
  password: string
}

/** Login result. */
export interface LoginResult {
  token: TokenPair
  user_id: EntityId
  nickname: string | null
  must_change_password: boolean
}

/** Signed-in business user. */
export interface PlatformUser {
  id: EntityId
  username: string | null
  nickname: string | null
  email: string | null
  phone: string | null
  avatar_url: string | null
  status: string
  registered_at: string | null
  last_login_at: string | null
}
