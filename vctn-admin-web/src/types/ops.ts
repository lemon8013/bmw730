/**
 * Operational payloads: notifications, system jobs, files and export jobs.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

/** `NotificationResponse`. */
export interface Notification {
  id: EntityId
  user_type: string
  user_id: EntityId
  notification_type: string
  title: string
  content: string
  payload?: Record<string, unknown> | null
  read_at?: IsoDateTime | null
  created_at: IsoDateTime
}

/** `NotificationPage` — the admin notification list is not a plain `Page`. */
export interface NotificationPage {
  items?: Notification[]
  total?: number
  page?: number
  page_size?: number
  unread_count?: number
}

/** `CreateNotificationRequest`. */
export interface CreateNotificationRequest {
  user_type: string
  user_id: EntityId
  notification_type: string
  title: string
  content: string
  payload?: Record<string, unknown> | null
}

/** `NotificationTypeStat`. */
export interface NotificationTypeStat {
  notification_type: string
  total: number
  unread: number
}

/** Query parameters of `GET /admin/notifications`. */
export interface NotificationQuery {
  user_type?: string
  user_id?: EntityId
  notification_type?: string
  unread_only?: boolean
  start?: IsoDateTime
  end?: IsoDateTime
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// System jobs
// ---------------------------------------------------------------------------

/** `JobResponse`. */
export interface SystemJob {
  id: EntityId
  job_code: string
  job_name: string
  job_type: string
  payload?: Record<string, unknown> | null
  status: string
  priority: number
  attempt_count: number
  max_attempts: number
  available_at: IsoDateTime
  started_at?: IsoDateTime | null
  finished_at?: IsoDateTime | null
  last_error?: string | null
  trace_id?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `JobCreateRequest`. */
export interface JobCreateRequest {
  job_code: string
  job_name: string
  job_type: string
  payload?: Record<string, unknown> | null
  priority?: number
  max_attempts?: number
}

/** Query parameters of `GET /jobs`. */
export interface JobQuery {
  status?: string
  job_type?: string
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

/** `FileResponse`. */
export interface FileRecord {
  id: EntityId
  owner_type?: string | null
  owner_id?: EntityId | null
  storage_provider: string
  bucket?: string | null
  object_key: string
  storage_key: string
  original_name?: string | null
  content_type?: string | null
  size_bytes?: number | null
  checksum?: string | null
  status: string
  metadata?: Record<string, unknown> | null
  created_at: IsoDateTime
  deleted_at?: IsoDateTime | null
}

/**
 * `FileCreateRequest`. The multipart upload endpoint is not implemented by the
 * backend, so the client registers metadata for an object it already knows.
 */
export interface FileCreateRequest {
  storage_provider?: string
  bucket?: string | null
  object_key: string
  original_name?: string | null
  content_type?: string | null
  size_bytes?: number | null
  checksum?: string | null
  owner_type?: string | null
  owner_id?: number | null
  metadata?: Record<string, unknown> | null
}

/** `FileCreatedResponse`. */
export interface FileCreated {
  id: EntityId
  storage_key: string
  status: string
}

/** Query parameters of `GET /files`. */
export interface FileQuery {
  page?: number
  page_size?: number
  status?: string
  owner_type?: string
}

// ---------------------------------------------------------------------------
// Export jobs
// ---------------------------------------------------------------------------

/** `ExportTaskResponse`. */
export interface ExportTask {
  id: EntityId
  export_type: string
  status: string
  file_id?: EntityId | null
  requested_by?: EntityId | null
  row_count?: number | null
  error_message?: string | null
  filter_json?: Record<string, unknown> | null
  created_at: IsoDateTime
  started_at?: IsoDateTime | null
  finished_at?: IsoDateTime | null
}

/** `CreateExportTaskRequest`. */
export interface CreateExportTaskRequest {
  export_type: string
  filter_json?: Record<string, unknown> | null
}

/** Query parameters of `GET /admin/export/tasks`. */
export interface ExportTaskQuery {
  export_type?: string
  status?: string
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

/** `SearchResultItem`. */
export interface SearchResultItem {
  resource_type: string
  id: EntityId
  title: string
  snippet?: string | null
  status?: string | null
  url?: string | null
}
