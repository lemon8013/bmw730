/**
 * Common helpers for the ops API modules.
 *
 * Every ops endpoint lives under the same `/ops` prefix, which the backend adds
 * when it mounts the routers; keeping it here means no call site repeats it and
 * no call site can invent a different one.
 */

import type { IsoDateTime } from '@/types/api'

/** Prefix shared by every ops endpoint. */
export const OPS_PREFIX = '/ops'

/** Join the ops prefix with a module path. */
export function opsPath(path: string): string {
  return `${OPS_PREFIX}${path}`
}

/**
 * Normalise a datetime query parameter.
 *
 * The backend parses ISO 8601 with a UTC offset. Element Plus hands over a
 * `Date`, which would serialise through `toString()` and produce a locale
 * dependent string, so it is converted explicitly.
 */
export function toIsoDateTime(value: Date | string | null | undefined): IsoDateTime | undefined {
  if (value === null || value === undefined || value === '') {
    return undefined
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? undefined : value.toISOString()
  }
  return value
}

/** Query parameters of a paginated list endpoint. */
export interface PageParams {
  page?: number
  page_size?: number
}

/** `page` / `page_size` as the backend expects them. */
export function pageQuery(page: number, pageSize: number): PageParams {
  return { page, page_size: pageSize }
}
