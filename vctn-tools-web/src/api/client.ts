import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import type { ApiEnvelope } from '@/types/api'

/** Base path of the single VCTN FastAPI backend. */
export const apiBaseUrl: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

/** Raised when the backend answers with a non-zero envelope code. */
export class ApiEnvelopeError extends Error {
  readonly code: number

  constructor(code: number, message: string) {
    super(message)
    this.name = 'ApiEnvelopeError'
    this.code = code
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
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

httpClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.headers.set('X-Trace-ID', newIdentifier())
  config.headers.set('X-Request-ID', newIdentifier())
  // Authorization and refresh handling belong to the authentication phase.
  return config
})

httpClient.interceptors.response.use(
  (response) => {
    const envelope = response.data as ApiEnvelope<unknown> | undefined
    if (envelope !== undefined && typeof envelope.code === 'number' && envelope.code !== 0) {
      return Promise.reject(new ApiEnvelopeError(envelope.code, envelope.message))
    }
    return response
  },
  (failure: unknown) => {
    if (axios.isAxiosError(failure)) {
      return Promise.reject(new ApiTransportError(failure.message, failure.response?.status))
    }
    return Promise.reject(
      failure instanceof Error ? failure : new ApiTransportError('unknown error'),
    )
  },
)

/** Return the shared axios instance. */
export function createApiClient(): AxiosInstance {
  return httpClient
}
