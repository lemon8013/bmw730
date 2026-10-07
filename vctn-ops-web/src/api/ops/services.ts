/** Monitored services and their dependency edges (`app/ops/services`). */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  Service,
  ServiceCreateRequest,
  ServiceDependency,
  ServiceDependencyCreateRequest,
  ServiceUpdateRequest,
} from '@/types/ops'

/** Filters accepted by `GET /ops/services`. */
export interface ServiceFilters {
  keyword?: string
  status?: string
  environment?: string
  serviceType?: string
  hostId?: string
}

/** `GET /ops/services` */
export function listServices(
  page = 1,
  pageSize = 20,
  filters: ServiceFilters = {},
): Promise<Page<Service>> {
  return get<Page<Service>>(opsPath('/services'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      status: filters.status ?? undefined,
      environment: filters.environment ?? undefined,
      service_type: filters.serviceType ?? undefined,
      host_id: filters.hostId ?? undefined,
    },
  })
}

/** `GET /ops/services/{service_id}` */
export function getService(serviceId: string): Promise<Service> {
  return get<Service>(opsPath(`/services/${encodeURIComponent(serviceId)}`))
}

/** `POST /ops/services` — requires `OPS_SERVICE_MANAGE`. */
export function createService(payload: ServiceCreateRequest): Promise<Service> {
  return post<Service>(opsPath('/services'), payload)
}

/** `PUT /ops/services/{service_id}` — requires `OPS_SERVICE_MANAGE`. */
export function updateService(serviceId: string, payload: ServiceUpdateRequest): Promise<Service> {
  return put<Service>(opsPath(`/services/${encodeURIComponent(serviceId)}`), payload)
}

/** `DELETE /ops/services/{service_id}` — requires `OPS_SERVICE_MANAGE`. */
export function deleteService(serviceId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/services/${encodeURIComponent(serviceId)}`))
}

/** `GET /ops/services/{service_id}/dependencies` */
export function listDependencies(
  serviceId: string,
  page = 1,
  pageSize = 20,
): Promise<Page<ServiceDependency>> {
  return get<Page<ServiceDependency>>(
    opsPath(`/services/${encodeURIComponent(serviceId)}/dependencies`),
    { params: { page, page_size: pageSize } },
  )
}

/** `POST /ops/services/{service_id}/dependencies` — requires `OPS_SERVICE_MANAGE`. */
export function addDependency(
  serviceId: string,
  payload: ServiceDependencyCreateRequest,
): Promise<ServiceDependency> {
  return post<ServiceDependency>(
    opsPath(`/services/${encodeURIComponent(serviceId)}/dependencies`),
    payload,
  )
}

/** `DELETE /ops/services/{service_id}/dependencies/{dependency_id}` — requires `OPS_SERVICE_MANAGE`. */
export function removeDependency(serviceId: string, dependencyId: string): Promise<DeleteResult> {
  return del<DeleteResult>(
    opsPath(
      `/services/${encodeURIComponent(serviceId)}/dependencies/${encodeURIComponent(dependencyId)}`,
    ),
  )
}
