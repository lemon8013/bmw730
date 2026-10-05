/**
 * Display helpers.
 *
 * Identifiers stay strings end to end: a BIGINT id must never pass through a
 * JavaScript number.
 */

import type { EntityId } from '@/types/api'

const DATE_TIME_FORMAT: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
}

const DATE_FORMAT: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}

/** Render an ISO 8601 timestamp in the local timezone, or an em dash. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', DATE_TIME_FORMAT).format(parsed)
}

/** Render an ISO 8601 date in the local timezone, or an em dash. */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return '—'
  }
  return new Intl.DateTimeFormat('zh-CN', DATE_FORMAT).format(parsed)
}

/** Render a byte count with a binary unit. */
export function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${unit === 0 ? size : size.toFixed(2)} ${units[unit]}`
}

/** Render a duration in milliseconds. */
export function formatDuration(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  if (value < 1000) {
    return `${value} ms`
  }
  return `${(value / 1000).toFixed(2)} s`
}

/** Render a plain number with thousand separators. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  return new Intl.NumberFormat('zh-CN').format(value)
}

/** Render a signed delta with an explicit sign. */
export function formatDelta(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

/**
 * Compare two BIGINT identifiers held as strings.
 *
 * String comparison is used deliberately: parsing to `number` would lose
 * precision above 2^53.
 */
export function sameId(left: EntityId | null | undefined, right: EntityId | null | undefined): boolean {
  if (left === null || left === undefined || right === null || right === undefined) {
    return false
  }
  return String(left) === String(right)
}

/** Format a `YYYY-MM-DD` string for a date picker value. */
export function toDateString(value: Date): string {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** The inclusive `[start, end]` range for the last `days` days. */
export function lastDaysRange(days: number): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - (days - 1))
  return { start: toDateString(start), end: toDateString(end) }
}
