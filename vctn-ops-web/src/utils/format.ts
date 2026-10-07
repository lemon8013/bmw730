/**
 * Display formatting helpers.
 *
 * The backend sends UTC ISO timestamps, byte counts and ratios; every page
 * renders them through these functions so one value is spelled the same way
 * everywhere and an absent value reads as `—` rather than `null`.
 */

/** Shown wherever the backend returned nothing. */
export const EMPTY = '—'

/** Render a nullable value, or `—` when it is absent. */
export function orEmpty(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return EMPTY
  }
  return String(value)
}

/** `2026-10-07 12:34:56` in the viewer's local zone, or `—`. */
export function formatDateTime(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return EMPTY
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return EMPTY
  }
  const pad = (part: number): string => String(part).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

/** `12:34:56`, for a series axis that already sits inside one day. */
export function formatTime(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return EMPTY
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return EMPTY
  }
  const pad = (part: number): string => String(part).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/** Render a ratio in `[0, 1]` as a percentage with one decimal. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY
  }
  return `${(value * 100).toFixed(digits)}%`
}

/** Render a plain ratio with two decimals (used where the value is not a share). */
export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY
  }
  return value.toFixed(2)
}

/** Human readable byte size. */
export function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(size >= 100 || unit === 0 ? 0 : 1)} ${units[unit]}`
}

/** Human readable duration from seconds. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return EMPTY
  }
  const total = Math.round(seconds)
  if (total < 60) {
    return `${total}s`
  }
  if (total < 3600) {
    return `${Math.floor(total / 60)}m ${total % 60}s`
  }
  if (total < 86400) {
    return `${Math.floor(total / 3600)}h ${Math.floor((total % 3600) / 60)}m`
  }
  return `${Math.floor(total / 86400)}d ${Math.floor((total % 86400) / 3600)}h`
}

/** Render a number with thousands separators, or `—`. */
export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY
  }
  return value.toLocaleString('zh-CN')
}
