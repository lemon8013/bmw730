/** Monitored hosts (`app/ops/hosts`). */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  Environment,
  Host,
  HostCreateRequest,
  HostGroup,
  HostUpdateRequest,
} from '@/types/ops'

/** Filters accepted by `GET /ops/hosts`. */
export interface HostFilters {
  keyword?: string
  status?: string
  environment?: string
  hostGroupId?: string
}

/** `GET /ops/hosts` */
export function listHosts(page = 1, pageSize = 20, filters: HostFilters = {}): Promise<Page<Host>> {
  return get<Page<Host>>(opsPath('/hosts'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      status: filters.status ?? undefined,
      environment: filters.environment ?? undefined,
      host_group_id: filters.hostGroupId ?? undefined,
    },
  })
}

/** `GET /ops/hosts/groups` */
export function listHostGroups(): Promise<HostGroup[]> {
  return get<HostGroup[]>(opsPath('/hosts/groups'))
}

/** `GET /ops/hosts/environments` */
export function listEnvironments(): Promise<Environment[]> {
  return get<Environment[]>(opsPath('/hosts/environments'))
}

/** `GET /ops/hosts/{host_id}` */
export function getHost(hostId: string): Promise<Host> {
  return get<Host>(opsPath(`/hosts/${encodeURIComponent(hostId)}`))
}

/** `POST /ops/hosts` — requires `OPS_HOST_MANAGE`. */
export function createHost(payload: HostCreateRequest): Promise<Host> {
  return post<Host>(opsPath('/hosts'), payload)
}

/** `PUT /ops/hosts/{host_id}` — requires `OPS_HOST_MANAGE`. */
export function updateHost(hostId: string, payload: HostUpdateRequest): Promise<Host> {
  return put<Host>(opsPath(`/hosts/${encodeURIComponent(hostId)}`), payload)
}

/** `DELETE /ops/hosts/{host_id}` — requires `OPS_HOST_MANAGE`. */
export function deleteHost(hostId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/hosts/${encodeURIComponent(hostId)}`))
}
