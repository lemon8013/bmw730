/**
 * Credential storage for the blog.
 *
 * The backend returns the Bearer pair in the response body — it does not set an
 * HttpOnly cookie — so the pair has to be kept by the browser. It lives in
 * `sessionStorage`: scoped to one tab, dropped when that tab closes, never
 * written to `localStorage`, never logged.
 *
 * The key prefix is `vctn.blog.` so a visitor signed in on one VCTN site is not
 * silently signed in on another.
 */

import type { TokenPair } from '@/types/auth'

const ACCESS_KEY = 'vctn.blog.access_token'
const REFRESH_KEY = 'vctn.blog.refresh_token'
const EXPIRES_KEY = 'vctn.blog.access_expires_at'

function read(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key)
  } catch {
    // A blocked storage API must not break the application.
    return null
  }
}

function write(key: string, value: string): void {
  try {
    window.sessionStorage.setItem(key, value)
  } catch {
    // Ignored on purpose: the session then simply does not survive a reload.
  }
}

function remove(key: string): void {
  try {
    window.sessionStorage.removeItem(key)
  } catch {
    // Ignored on purpose.
  }
}

/** An access token together with the moment it stops being usable. */
export interface StoredCredentials {
  accessToken: string
  refreshToken: string
  /** Epoch milliseconds; the token is refreshed slightly before this. */
  expiresAt: number
}

/** How many milliseconds before expiry a proactive refresh starts. */
export const REFRESH_SKEW_MS = 30_000

/** Return the stored credentials, or `null` when there is no usable session. */
export function readCredentials(): StoredCredentials | null {
  const accessToken = read(ACCESS_KEY)
  const refreshToken = read(REFRESH_KEY)
  if (!accessToken || !refreshToken) {
    return null
  }
  const rawExpiry = read(EXPIRES_KEY)
  const expiresAt = rawExpiry === null ? 0 : Number.parseInt(rawExpiry, 10)
  return {
    accessToken,
    refreshToken,
    expiresAt: Number.isFinite(expiresAt) ? expiresAt : 0,
  }
}

/** Persist a freshly issued token pair. */
export function writeCredentials(token: TokenPair): void {
  write(ACCESS_KEY, token.access_token)
  write(REFRESH_KEY, token.refresh_token)
  write(EXPIRES_KEY, String(Date.now() + token.expires_in * 1000))
}

/** Forget the current session. */
export function clearCredentials(): void {
  remove(ACCESS_KEY)
  remove(REFRESH_KEY)
  remove(EXPIRES_KEY)
}

/** Whether the access token is missing or close enough to expiry to refresh. */
export function accessTokenNeedsRefresh(credentials: StoredCredentials): boolean {
  return credentials.expiresAt - REFRESH_SKEW_MS <= Date.now()
}
