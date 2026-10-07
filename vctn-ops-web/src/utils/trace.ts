/**
 * Trace context.
 *
 * Every outbound request carries a trace id and a request id; the id the
 * backend echoes back is remembered so an error page can show it.
 */

const TRACE_HEADER = 'X-Trace-ID'
const REQUEST_HEADER = 'X-Request-ID'

/** Generate a 32 character hex identifier. */
export function newIdentifier(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    crypto.getRandomValues(bytes)
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  // Trace ids are correlation aids, not secrets: a last-resort fallback keeps
  // the request pipeline working where `crypto` is unavailable.
  return Math.random().toString(16).slice(2).padEnd(32, '0').slice(0, 32)
}

/** One request's trace identifiers. */
export interface TraceContext {
  traceId: string
  requestId: string
}

/** Create a fresh trace context for one request. */
export function createTraceContext(): TraceContext {
  return { traceId: newIdentifier(), requestId: newIdentifier() }
}

/** Header names, exported so nothing re-declares a literal. */
export const TRACE_HEADERS = { trace: TRACE_HEADER, request: REQUEST_HEADER } as const
