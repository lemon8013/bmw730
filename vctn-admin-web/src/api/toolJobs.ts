/** Tool job inspection (`app/tools/jobs`). */

import { get, post } from '@/api/client'
import type { ToolJob, ToolJobList } from '@/types/tools'

/** `GET /tools/jobs` */
export function listToolJobs(query: {
  status?: string
  job_type?: string
  page?: number
  page_size?: number
} = {}): Promise<ToolJobList> {
  return get<ToolJobList>('/tools/jobs', { params: query })
}

/** `GET /tools/jobs/{job_id}` */
export function getToolJob(jobId: string): Promise<ToolJob> {
  return get<ToolJob>(`/tools/jobs/${jobId}`)
}

/** `POST /tools/jobs/{job_id}/retry` */
export function retryToolJob(jobId: string): Promise<ToolJob> {
  return post<ToolJob>(`/tools/jobs/${jobId}/retry`)
}
