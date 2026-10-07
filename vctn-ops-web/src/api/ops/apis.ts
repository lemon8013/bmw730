/**
 * Monitored API endpoints (`app/ops/apis`).
 *
 * A read-only domain: endpoints are produced by normalising access logs, so
 * there is nothing to create or edit by hand.
 */

import { get } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { EndpointMetrics, MonitoredEndpoint } from '@/types/ops'

/** Filters accepted by `GET /ops/apis`. */
export interface EndpointFilters {
  keyword?: string
  httpMethod?: string
  serviceId?: string
  environment?: string
  isMonitored?: boolean
}

/** `GET /ops/apis` */
export function listEndpoints(
  page = 1,
  pageSize = 20,
  filters: EndpointFilters = {},
): Promise<Page<MonitoredEndpoint>> {
  return get<Page<MonitoredEndpoint>>(opsPath('/apis'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      http_method: filters.httpMethod ?? undefined,
      service_id: filters.serviceId ?? undefined,
      environment: filters.environment ?? undefined,
      is_monitored: filters.isMonitored ?? undefined,
    },
  })
}

/** `GET /ops/apis/{endpoint_id}` */
export function getEndpoint(endpointId: string): Promise<MonitoredEndpoint> {
  return get<MonitoredEndpoint>(opsPath(`/apis/${encodeURIComponent(endpointId)}`))
}

/** `GET /ops/apis/{endpoint_id}/metrics` */
export function getEndpointMetrics(endpointId: string, hours = 24): Promise<EndpointMetrics> {
  return get<EndpointMetrics>(opsPath(`/apis/${encodeURIComponent(endpointId)}/metrics`), {
    params: { hours },
  })
}
