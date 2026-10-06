/**
 * Business-user authentication types.
 *
 * Mirrors `app/platform/auth/schema.py`. The tool portal is anonymous by
 * default; signing in is optional and only unlocks the personal endpoints
 * (`/tools/recent`, `/tools/usage/*`) that require a business identity.
 */

/** BIGINT identifiers are serialised as strings by the backend. */
export type EntityId = string

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

/** Refresh payload. */
export interface RefreshRequest {
  refresh_token: string
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

/** Self service password change. */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}
