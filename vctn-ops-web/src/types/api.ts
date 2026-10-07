/**
 * Wire format shared with the single VCTN FastAPI backend.
 *
 * Every response is wrapped in the same envelope and every BIGINT identifier is
 * serialised as a string, so no identifier may ever be held in a `number`.
 */

/** Unified response envelope returned by every endpoint. */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

/** BIGINT identifiers are serialised as strings by the backend. */
export type EntityId = string

/** ISO 8601 timestamp, always UTC as produced by the backend. */
export type IsoDateTime = string

/** A page of rows, as returned by every list endpoint. */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages?: number
}

/** Query parameters shared by every paginated list endpoint. */
export interface PageQuery {
  page?: number
  page_size?: number
}

/** An empty page, used before the first response arrives. */
export function emptyPage<T>(pageSize = 20): Page<T> {
  return { items: [], total: 0, page: 1, page_size: pageSize }
}

/**
 * Error codes the backend actually emits (see `app/core/exceptions.py`).
 * Kept in one place so the error handler never has to guess a number.
 */
export const ERROR_CODE = {
  business: 400001,
  authentication: 401001,
  authorization: 403001,
  dataScope: 403002,
  notFound: 404001,
  conflict: 409001,
  idempotency: 409002,
  concurrency: 409003,
  validation: 422001,
  rateLimit: 429001,
  quotaExceeded: 429002,
  system: 500000,
  serviceUnavailable: 503001,
} as const

/** Error codes that mean "this identity may no longer act". */
export const SESSION_INVALID_CODES: readonly number[] = [ERROR_CODE.authentication]

/** Error codes that mean "the identity is valid but this action is refused". */
export const FORBIDDEN_CODES: readonly number[] = [
  ERROR_CODE.authorization,
  ERROR_CODE.dataScope,
]
