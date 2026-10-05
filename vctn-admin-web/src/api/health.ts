/**
 * System probes.
 *
 * These live at the application root (`/health`, `/ready`, `/version`), not
 * under the business prefix `/api/v1`. Every call therefore opts out of the
 * shared base URL with `vctn.rawUrl`, otherwise axios would join the path and
 * request `/api/v1/version`, which does not exist.
 */

import { get } from '@/api/client'

/** Payload of the version probe. */
export interface BackendVersion {
  app_name: string
  version: string
  environment: string
}

/** Payload of the liveness probe. */
export interface HealthStatus {
  status: string
}

/** Liveness probe. */
export function health(): Promise<HealthStatus> {
  return get<HealthStatus>('/health', { vctn: { rawUrl: true, anonymous: true } })
}

/** Readiness probe. */
export function ready(): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>('/ready', { vctn: { rawUrl: true, anonymous: true } })
}

/** Build version reported by the running backend. */
export function version(): Promise<BackendVersion> {
  return get<BackendVersion>('/version', { vctn: { rawUrl: true, anonymous: true } })
}
