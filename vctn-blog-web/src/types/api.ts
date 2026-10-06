/**
 * Wire format shared with the single VCTN FastAPI backend.
 */

/** Unified response envelope returned by every endpoint. */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

/** Server-side page envelope. */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** BIGINT identifiers are serialised as strings by the backend. */
export type EntityId = string
