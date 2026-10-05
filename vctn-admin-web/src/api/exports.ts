/** Export job console (`app/admin/export`). */

import { get, post } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateExportTaskRequest,
  ExportTask,
  ExportTaskQuery,
} from '@/types/ops'

/** `GET /admin/export/tasks` */
export function listExportTasks(query: ExportTaskQuery = {}): Promise<Page<ExportTask>> {
  return get<Page<ExportTask>>('/admin/export/tasks', { params: query })
}

/** `POST /admin/export/tasks` */
export function createExportTask(payload: CreateExportTaskRequest): Promise<ExportTask> {
  return post<ExportTask>('/admin/export/tasks', payload, {
    vctn: {
      idempotencyKey: `create-export:${payload.export_type}:${JSON.stringify(payload.filter_json ?? {})}`,
    },
  })
}

/** `GET /admin/export/tasks/{task_id}` */
export function getExportTask(taskId: string): Promise<ExportTask> {
  return get<ExportTask>(`/admin/export/tasks/${taskId}`)
}

/** `POST /admin/export/tasks/{task_id}/retry` */
export function retryExportTask(taskId: string): Promise<ExportTask> {
  return post<ExportTask>(`/admin/export/tasks/${taskId}/retry`)
}
