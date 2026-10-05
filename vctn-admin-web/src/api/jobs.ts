/** System job console (`app/system/jobs`). */

import { get, post } from '@/api/client'
import type { Page } from '@/types/api'
import type { JobCreateRequest, JobQuery, SystemJob } from '@/types/ops'

/** `GET /jobs` */
export function listJobs(query: JobQuery = {}): Promise<Page<SystemJob>> {
  return get<Page<SystemJob>>('/jobs', { params: query })
}

/** `GET /jobs/{job_id}` */
export function getJob(jobId: string): Promise<SystemJob> {
  return get<SystemJob>(`/jobs/${jobId}`)
}

/** `POST /jobs` */
export function createJob(payload: JobCreateRequest): Promise<SystemJob> {
  return post<SystemJob>('/jobs', payload, {
    vctn: { idempotencyKey: `create-job:${payload.job_code}` },
  })
}

/** `POST /jobs/{job_id}/retry` */
export function retryJob(jobId: string): Promise<SystemJob> {
  return post<SystemJob>(`/jobs/${jobId}/retry`)
}
