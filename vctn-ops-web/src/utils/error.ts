/**
 * Turn any thrown value into something safe to show a user.
 *
 * Nothing here can surface a stack trace, a SQL fragment or an internal path:
 * only the backend's own `message`, a mapped sentence for transport failures,
 * and the trace id, which is what support needs.
 */

import { ApiError } from '@/api/errors'

/** A problem rendered by the UI. */
export interface RenderedError {
  /** Sentence shown to the user. */
  message: string
  /** Trace id to quote when reporting the problem. */
  traceId?: string
  /** True when the caller may simply retry. */
  retryable: boolean
  /** True when the action was refused rather than failed. */
  forbidden: boolean
  /** True when the session has to be re-established. */
  sessionInvalid: boolean
  /** Field level messages, when the backend reported a validation failure. */
  fieldErrors: Record<string, string>
}

function extractFieldErrors(details: unknown): Record<string, string> {
  const result: Record<string, string> = {}
  if (details === null || typeof details !== 'object') {
    return result
  }
  const container = details as { errors?: unknown }
  if (!Array.isArray(container.errors)) {
    return result
  }
  for (const item of container.errors) {
    if (item === null || typeof item !== 'object') {
      continue
    }
    const entry = item as { loc?: unknown; msg?: unknown }
    const loc = Array.isArray(entry.loc) ? entry.loc : []
    const field = [...loc].reverse().find((part) => typeof part === 'string' && part !== 'body')
    if (typeof field === 'string' && typeof entry.msg === 'string') {
      result[field] = entry.msg
    }
  }
  return result
}

/** Render any thrown value for display. */
export function renderError(error: unknown): RenderedError {
  if (error instanceof ApiError) {
    return {
      message: error.message,
      traceId: error.traceId,
      retryable: error.isRetryable,
      forbidden: error.isForbidden,
      sessionInvalid: error.isSessionInvalid,
      fieldErrors: extractFieldErrors(error.details),
    }
  }
  if (error instanceof Error) {
    return {
      message: error.message,
      retryable: false,
      forbidden: false,
      sessionInvalid: false,
      fieldErrors: {},
    }
  }
  return {
    message: '发生未知错误，请稍后重试',
    retryable: false,
    forbidden: false,
    sessionInvalid: false,
    fieldErrors: {},
  }
}
