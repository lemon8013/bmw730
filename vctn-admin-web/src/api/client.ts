/**
 * The single authenticated axios client.
 *
 * Responsibilities:
 * * attach `Authorization`, `X-Trace-ID`, `X-Request-ID` and, for idempotent
 *   writes, `Idempotency-Key`;
 * * unwrap the unified `{ code, message, data }` envelope so callers receive
 *   `data` directly;
 * * turn every failure into an {@link ApiError};
 * * on a session-invalid failure, refresh once (single flight), replay the
 *   original request and never loop.
 */

import axios, {
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

import { readCredentials, clearCredentials } from '@/api/credentials'
import { apiBaseUrl } from '@/api/endpoint'
import { ApiError, TRANSPORT_CODE } from '@/api/errors'
import { refreshTokens } from '@/api/refresh'
import type { ApiEnvelope } from '@/types/api'
import { createTraceContext, TRACE_HEADERS } from '@/utils/trace'

/** Session-invalid envelope code emitted by the backend. */
const CODE_AUTHENTICATION = 401001

/** Extra, client-only request options. */
export interface RequestOptions {
  /** Send this value as `Idempotency-Key`. */
  idempotencyKey?: string
  /** Do not attach an `Authorization` header. */
  anonymous?: boolean
  /** Do not attempt a refresh-and-replay on a session-invalid failure. */
  skipAuthRetry?: boolean
  /**
   * Treat `url` as already rooted at the server origin.
   *
   * The business API lives under `/api/v1`, but the system probes (`/health`,
   * `/ready`, `/version`) sit at the application root. Without this flag axios
   * would join them with the base URL and request `/api/v1/version`.
   */
  rawUrl?: boolean
}

declare module 'axios' {
  export interface AxiosRequestConfig {
    vctn?: RequestOptions
  }
}

const configuredTimeout = Number.parseInt(
  (import.meta.env.VITE_API_TIMEOUT_MS as string | undefined) ?? '',
  10,
)

/** Every request in this application shares one interceptor chain. */
export const httpClient: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  // Login verifies an argon2 hash (~3s) and a cold backend can take far longer,
  // so keep the default well above the worst observed latency.
  timeout: Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 45000,
  headers: { 'Content-Type': 'application/json' },
})

function toApiError(error: unknown, traceId: string): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return new ApiError({
        message: '请求超时，请稍后重试',
        code: TRANSPORT_CODE.timeout,
        httpStatus: status,
        traceId,
      })
    }
    if (error.response === undefined) {
      return new ApiError({
        message: '无法连接到服务器，请检查网络或后端服务状态',
        code: TRANSPORT_CODE.network,
        traceId,
      })
    }
    const envelope = error.response.data as ApiEnvelope<unknown> | undefined
    if (envelope !== undefined && typeof envelope.code === 'number') {
      return new ApiError({
        message: envelope.message,
        code: envelope.code,
        httpStatus: status,
        traceId,
        details: envelope.data,
      })
    }
    return new ApiError({
      message: error.message,
      code: TRANSPORT_CODE.malformed,
      httpStatus: status,
      traceId,
    })
  }
  if (error instanceof Error) {
    // A plain `Error` here means the request pipeline failed before axios could
    // model the failure — an adapter rejection, a proxy fault, a DNS problem
    // surfaced by the runtime. That is a connectivity failure, so it is reported
    // as one instead of the unhelpful "unexpected client failure".
    return new ApiError({
      message: '无法连接到服务器，请检查网络或后端服务状态',
      code: TRANSPORT_CODE.network,
      traceId,
    })
  }
  return new ApiError({
    message: 'unexpected client failure',
    code: TRANSPORT_CODE.unknown,
    traceId,
  })
}

function isSessionInvalidFailure(failure: unknown): boolean {
  if (!axios.isAxiosError(failure)) {
    return false
  }
  if (failure.response?.status === 401) {
    return true
  }
  const body = failure.response?.data as ApiEnvelope<unknown> | undefined
  return body !== undefined && body.code === CODE_AUTHENTICATION
}

httpClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const headers = config.headers instanceof AxiosHeaders ? config.headers : new AxiosHeaders()
  const trace = createTraceContext()
  headers.set(TRACE_HEADERS.trace, trace.traceId)
  headers.set(TRACE_HEADERS.request, trace.requestId)
  config.headers = headers
  config.vctn = config.vctn ?? {}

  const credentials = readCredentials()
  if (config.vctn.anonymous !== true && credentials !== null) {
    headers.set('Authorization', `Bearer ${credentials.accessToken}`)
  }
  if (config.vctn.idempotencyKey) {
    headers.set('Idempotency-Key', config.vctn.idempotencyKey)
  }
  return config
})

httpClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const envelope = response.data as ApiEnvelope<unknown> | undefined
    if (envelope === undefined || typeof envelope !== 'object' || !('code' in envelope)) {
      return Promise.reject(
        new ApiError({
          message: '服务端返回了无法识别的响应格式',
          code: TRANSPORT_CODE.malformed,
          httpStatus: response.status,
        }),
      )
    }
    if (envelope.code !== 0) {
      const echoed = response.headers[TRACE_HEADERS.trace.toLowerCase()]
      return Promise.reject(
        new ApiError({
          message: envelope.message,
          code: envelope.code,
          httpStatus: response.status,
          traceId: typeof echoed === 'string' ? echoed : undefined,
          details: envelope.data,
        }),
      )
    }
    return response
  },
  async (failure: unknown) => {
    const config = axios.isAxiosError(failure) ? failure.config : undefined
    const options: RequestOptions = config?.vctn ?? {}

    if (
      config !== undefined &&
      options.skipAuthRetry !== true &&
      isSessionInvalidFailure(failure)
    ) {
      try {
        await refreshTokens(true)
      } catch {
        clearCredentials()
        throw new ApiError({
          message: '登录状态已失效，请重新登录',
          code: CODE_AUTHENTICATION,
          httpStatus: 401,
        })
      }
      const replayed: AxiosRequestConfig = {
        ...config,
        vctn: { ...options, skipAuthRetry: true },
      }
      try {
        return await httpClient.request(replayed)
      } catch (replayFailure) {
        throw toApiError(replayFailure, '')
      }
    }
    throw toApiError(failure, '')
  },
)

/** Perform a request and return the unwrapped `data` payload. */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const options = config.vctn
  const prepared: AxiosRequestConfig =
    options?.rawUrl === true ? { ...config, baseURL: '' } : config
  const response = await httpClient.request<ApiEnvelope<T>>(prepared)
  return response.data.data as T
}

/** `GET` returning the unwrapped payload. */
export function get<T>(url: string, config: AxiosRequestConfig = {}): Promise<T> {
  return request<T>({ ...config, method: 'GET', url })
}

/** `POST` returning the unwrapped payload. */
export function post<T>(url: string, data?: unknown, config: AxiosRequestConfig = {}): Promise<T> {
  return request<T>({ ...config, method: 'POST', url, data })
}

/** `PUT` returning the unwrapped payload. */
export function put<T>(url: string, data?: unknown, config: AxiosRequestConfig = {}): Promise<T> {
  return request<T>({ ...config, method: 'PUT', url, data })
}

/** `DELETE` returning the unwrapped payload. */
export function del<T>(url: string, config: AxiosRequestConfig = {}): Promise<T> {
  return request<T>({ ...config, method: 'DELETE', url })
}
