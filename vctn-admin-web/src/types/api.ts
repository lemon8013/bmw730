/**
 * Wire format shared with the single VCTN FastAPI backend.
 */

/** Unified response envelope returned by every endpoint. */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

/** BIGINT identifiers are serialised as strings by the backend. */
export type EntityId = string
