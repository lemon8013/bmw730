/**
 * Token refresh for the tool portal.
 *
 * The refresh call uses its own axios instance so it can never re-enter the
 * authenticated interceptor, and it is **single flight**: concurrent 401s share
 * one in-flight refresh instead of each starting their own. A failed refresh
 * clears the session exactly once and every waiting request fails with the same
 * error, so the UI sees one consistent "session ended" event.
 *
 * This module deliberately does not import `@/api/client` — the reverse
 * direction is the one that exists — which is why `apiBaseUrl` lives in
 * `@/api/endpoint`.
 */

import axios, { type AxiosInstance } from 'axios'

import { accessTokenNeedsRefresh, clearCredentials, readCredentials, writeCredentials } from '@/api/credentials'
import { apiBaseUrl } from '@/api/endpoint'
import type { ApiEnvelope } from '@/types/api'
import type { RefreshRequest, TokenPair } from '@/types/auth'

/** Refresh path of the platform (business user) auth module. */
const REFRESH_PATH = '/auth/refresh'

/** Called once whenever the session cannot be restored. */
export type SessionExpiredHandler = () => void

let sessionExpiredHandler: SessionExpiredHandler | null = null

/** Register the callback that runs when the session is gone for good. */
export function onSessionExpired(handler: SessionExpiredHandler | null): void {
  sessionExpiredHandler = handler
}

/** The raw instance used exclusively for refreshing. */
const refreshClient: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

/** The refresh currently in flight, shared by every waiting caller. */
let inFlight: Promise<TokenPair> | null = null

async function requestRefresh(refreshToken: string): Promise<TokenPair> {
  const payload: RefreshRequest = { refresh_token: refreshToken }
  const response = await refreshClient.post<ApiEnvelope<TokenPair>>(REFRESH_PATH, payload)
  const envelope = response.data
  if (envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message || 'token refresh failed')
  }
  writeCredentials(envelope.data)
  return envelope.data
}

/**
 * Refresh the access token, starting at most one refresh at a time.
 *
 * `force` bypasses the "still valid" short circuit; it is used by the 401 retry
 * path, where the server has already rejected the current token.
 */
export async function refreshTokens(force = false): Promise<TokenPair> {
  const credentials = readCredentials()
  if (credentials === null) {
    throw new Error('no session to refresh')
  }
  if (!force && !accessTokenNeedsRefresh(credentials)) {
    return {
      access_token: credentials.accessToken,
      refresh_token: credentials.refreshToken,
      token_type: 'Bearer',
      expires_in: Math.max(0, Math.floor((credentials.expiresAt - Date.now()) / 1000)),
      refresh_expires_in: 0,
    }
  }
  if (inFlight === null) {
    inFlight = requestRefresh(credentials.refreshToken)
      .catch((error: unknown) => {
        clearCredentials()
        sessionExpiredHandler?.()
        throw error
      })
      .finally(() => {
        inFlight = null
      })
  }
  return inFlight
}

/** End the session locally and notify whoever is listening. */
export function endSession(): void {
  clearCredentials()
  sessionExpiredHandler?.()
}
