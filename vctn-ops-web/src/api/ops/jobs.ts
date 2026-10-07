/**
 * Job runs (`app/ops/jobs`).
 *
 * `retry` and `stop` are high risk: the backend validates that the current
 * status allows the action and writes the audit record, so an impossible
 * request is refused rather than silently mutating the row.
 */

import { get, post } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { JobRun, JobStatistics } from '@/types/ops'

/** Filters accepted by `GET /ops/jobs`. */
export interface JobFilters {
  status?: string
  definitionCode?: string
  startAt?: Date | string | null
  endAt?: Date | string | null
}

/** `GET /ops/jobs` */
export function listJobs(page = 1, pageSize = 20, filters: JobFilters = {}): Promise<Page<JobRun>> {
  return get<Page<JobRun>>(opsPath('/jobs'), {
    params: {
      page,
      page_size: pageSize,
      status: filters.status ?? undefined,
      definition_code: filters.definitionCode ?? undefined,
      start_at: toIsoDateTime(filters.startAt),
      end_at: toIsoDateTime(filters.endAt),
    },
  })
}

/** `GET /ops/jobs/statistics` */
export function fetchJobStatistics(days = 7): Promise<JobStatistics> {
  return get<JobStatistics>(opsPath('/jobs/statistics'), { params: { days } })
}

/** `GET /ops/jobs/{job_id}` */
export function getJob(jobId: string): Promise<JobRun> {
  return get<JobRun>(opsPath(`/jobs/${encodeURIComponent(jobId)}`))
}

/** `POST /ops/jobs/{job_id}/retry` — requires `OPS_JOB_MANAGE`. */
export function retryJob(jobId: string): Promise<JobRun> {
  return post<JobRun>(opsPath(`/jobs/${encodeURIComponent(jobId)}/retry`), undefined)
}

/** `POST /ops/jobs/{job_id}/stop` — requires `OPS_JOB_MANAGE`. */
export function stopJob(jobId: string): Promise<JobRun> {
  return post<JobRun>(opsPath(`/jobs/${encodeURIComponent(jobId)}/stop`), undefined)
}
