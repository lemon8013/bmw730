/**
 * Normalised API failure.
 *
 * Every transport failure and every non-zero envelope becomes one of these, so
 * no page has to inspect an axios error shape.
 */

import { ERROR_CODE, FORBIDDEN_CODES, SESSION_INVALID_CODES } from '@/types/api'

/** Raised when the request never produced a usable response. */
export class ApiError extends Error {
  /** Backend envelope code, or a synthetic one for transport failures. */
  readonly code: number
  /** HTTP status, when a response was received. */
  readonly httpStatus: number | undefined
  /** Trace id reported by the caller or echoed by the backend. */
  readonly traceId: string | undefined
  /** Structured payload the backend attached to the failure. */
  readonly details: unknown

  constructor(options: {
    message: string
    code: number
    httpStatus?: number
    traceId?: string
    details?: unknown
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.code = options.code
    this.httpStatus = options.httpStatus
    this.traceId = options.traceId
    this.details = options.details
  }

  /** Whether the session must be re-established. */
  get isSessionInvalid(): boolean {
    return SESSION_INVALID_CODES.includes(this.code as never) || this.httpStatus === 401
  }

  /** Whether the identity is valid but the action is refused. */
  get isForbidden(): boolean {
    return FORBIDDEN_CODES.includes(this.code as never) || this.httpStatus === 403
  }

  /** Whether the failure is a validation problem the user can correct. */
  get isValidation(): boolean {
    return this.code === ERROR_CODE.validation || this.httpStatus === 422
  }

  /** Whether retrying later has a realistic chance of succeeding. */
  get isRetryable(): boolean {
    return (
      this.code === ERROR_CODE.system ||
      this.code === ERROR_CODE.serviceUnavailable ||
      this.httpStatus === 502 ||
      this.httpStatus === 503 ||
      this.httpStatus === 504
    )
  }

  /** Whether the failure is a rate limit or quota refusal. */
  get isThrottled(): boolean {
    return this.code === ERROR_CODE.rateLimit || this.code === ERROR_CODE.quotaExceeded
  }
}

/** Synthetic codes used when the backend could not be reached at all. */
export const TRANSPORT_CODE = {
  network: -1,
  timeout: -2,
  cancelled: -3,
  malformed: -4,
  unknown: -5,
} as const
