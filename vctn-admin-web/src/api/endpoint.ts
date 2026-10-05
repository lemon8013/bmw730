/**
 * Single source of truth for the backend base URL.
 *
 * Kept in its own module so both the authenticated client and the refresh
 * client read the same value without importing each other.
 */

const FALLBACK_BASE_URL = '/api/v1'

/** Base path of the single VCTN FastAPI backend. */
export const apiBaseUrl: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || FALLBACK_BASE_URL

/** Application code reported to analytics and to the backend. */
export const appCode = 'vctn-admin-web'

/** Application version reported to analytics. */
export const appVersion: string = __APP_VERSION__
