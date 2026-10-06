import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import { readCredentials } from '@/api/credentials'
import { apiBaseUrl } from '@/api/endpoint'
import { refreshTokens } from '@/api/session'
import type { ApiEnvelope } from '@/types/api'

export { apiBaseUrl }

/** Raised when the backend answers with a non-zero envelope code. */
export class ApiEnvelopeError extends Error {
  readonly code: number
  /** The envelope `data` payload, kept so validation details survive. */
  readonly details: unknown

  constructor(code: number, message: string, details: unknown = null) {
    super(message)
    this.name = 'ApiEnvelopeError'
    this.code = code
    this.details = details
  }
}

/** Raised for transport level failures (network, timeout, HTTP status). */
export class ApiTransportError extends Error {
  readonly status: number | undefined

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiTransportError'
    this.status = status
  }
}

function newIdentifier(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return Math.random().toString(16).slice(2).padEnd(32, '0').slice(0, 32)
}

export const httpClient: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  // Login verifies an argon2 hash (~3s); keep headroom for a cold backend.
  timeout: 45000,
  headers: { 'Content-Type': 'application/json' },
})

httpClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  config.headers.set('X-Trace-ID', newIdentifier())
  config.headers.set('X-Request-ID', newIdentifier())

  // Reading the blog is anonymous, so a missing token is normal and simply
  // means "no Authorization header". When a session exists it is attached, and
  // a token close to expiry is renewed proactively so the request never leaves
  // with a stale Bearer.
  const credentials = readCredentials()
  if (credentials !== null) {
    try {
      const token = await refreshTokens()
      config.headers.set('Authorization', `${token.token_type || 'Bearer'} ${token.access_token}`)
    } catch {
      throw new ApiTransportError('session expired', 401)
    }
  }
  return config
})

httpClient.interceptors.response.use(
  (response) => {
    const envelope = response.data as ApiEnvelope<unknown> | undefined
    if (envelope !== undefined && typeof envelope.code === 'number' && envelope.code !== 0) {
      return Promise.reject(new ApiEnvelopeError(envelope.code, envelope.message, envelope.data))
    }
    return response
  },
  async (failure: unknown) => {
    if (!axios.isAxiosError(failure)) {
      return Promise.reject(
        failure instanceof Error ? failure : new ApiTransportError('unknown error'),
      )
    }
    const status = failure.response?.status
    const config = failure.config
    // One retry after a forced refresh: the proactive refresh races with the
    // server's own expiry clock, so a 401 can still happen on a live session.
    if (status === 401 && config !== undefined && !(config as { _retried?: boolean })._retried) {
      ;(config as { _retried?: boolean })._retried = true
      try {
        const token = await refreshTokens(true)
        config.headers.set('Authorization', `${token.token_type || 'Bearer'} ${token.access_token}`)
        return httpClient.request(config)
      } catch {
        // Fall through to the generic 401 below.
      }
    }
    return Promise.reject(new ApiTransportError(failure.message, status))
  },
)

/** Return the shared axios instance. */
export function createApiClient(): AxiosInstance {
  return httpClient
}
