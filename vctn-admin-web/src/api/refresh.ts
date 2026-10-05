/**
 * Token refresh.
 *
 * The refresh call uses its own axios instance so it can never re-enter the
 * authenticated interceptor, and it is **single flight**: concurrent 401s share
 * one in-flight refresh instead of each starting their own. A failed refresh
 * clears the session exactly once and every waiting request fails with the same
 * error, so the UI has one consistent "session ended" event.
 */

import axios, { type AxiosInstance } from 'axios'

import {
  accessTokenNeedsRefresh,
  clearCredentials,
  readCredentials,
  writeCredentials,
} from '@/api/credentials'
import { ApiError, TRANSPORT_CODE } from '@/api/errors'
import { apiBaseUrl } from '@/api/endpoint'
import type { ApiEnvelope } from '@/types/api'
import type { RefreshRequest, TokenPair } from '@/types/auth'
import { createTraceContext, TRACE_HEADERS } from '@/utils/trace'

/** Refresh path, relative to the API base URL. */
const REFRESH_PATH = '/admin/auth/refresh'

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

function refreshError(message: string, cause?: unknown): ApiError {
  const base = new ApiError({ message, code: TRANSPORT_CODE.unknown })
  return cause instanceof ApiError ? cause : base
}

async function requestRefresh(refreshToken: string): Promise<TokenPair> {
  const trace = createTraceContext()
  const payload: RefreshRequest = { refresh_token: refreshToken }
  try {
    const response = await refreshClient.post<ApiEnvelope<TokenPair>>(REFRESH_PATH, payload, {
      headers: {
        [TRACE_HEADERS.trace]: trace.traceId,
        [TRACE_HEADERS.request]: trace.requestId,
      },
    })
    const envelope = response.data
    if (envelope.code !== 0 || envelope.data === null) {
      throw new ApiError({
        message: envelope.message,
        code: envelope.code,
        httpStatus: response.status,
        traceId: trace.traceId,
      })
    }
    writeCredentials(envelope.data)
    return envelope.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      throw new ApiError({
        message: error.message,
        code: TRANSPORT_CODE.network,
        httpStatus: status,
        traceId: trace.traceId,
      })
    }
    throw refreshError('token refresh failed', error)
  }
}

/**
 * Refresh the access token, starting at most one refresh at a time.
 *
 * `force` bypasses the "still valid" short circuit; it is used by the 401
 * retry path, where the server has already rejected the current token.
 */
export async function refreshTokens(force = false): Promise<TokenPair> {
  const credentials = readCredentials()
  if (credentials === null) {
    throw new ApiError({ message: 'no session to refresh', code: TRANSPORT_CODE.unknown })
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
