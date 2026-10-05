/**
 * Audit, trace and log payloads, matching `app/admin/audit/schema.py` and
 * `app/admin/logs/schema.py`.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

/** `AuditLogResponse`. */
export interface AuditLog {
  id: EntityId
  trace_id?: string | null
  request_id?: string | null
  operator_id?: EntityId | null
  operator_username?: string | null
  action: string
  resource_type?: string | null
  resource_id?: string | null
  before_data?: Record<string, unknown> | null
  after_data?: Record<string, unknown> | null
  result: string
  error_code?: string | null
  ip?: string | null
  user_agent?: string | null
  created_at: IsoDateTime
}

/** `SecurityLogResponse`. */
export interface SecurityLog {
  id: EntityId
  trace_id?: string | null
  user_id?: EntityId | null
  event_type: string
  result: string
  error_code?: string | null
  ip?: string | null
  user_agent?: string | null
  metadata?: Record<string, unknown> | null
  created_at: IsoDateTime
}

/** `OperationLogResponse`. */
export interface OperationLog {
  id: EntityId
  trace_id?: string | null
  request_id?: string | null
  operator_id?: EntityId | null
  operation: string
  resource_type?: string | null
  resource_id?: string | null
  result: string
  metadata?: Record<string, unknown> | null
  created_at: IsoDateTime
}

/** `AccessLogResponse`. */
export interface AccessLog {
  id: EntityId
  trace_id?: string | null
  request_id?: string | null
  user_id?: EntityId | null
  method: string
  path: string
  status_code?: number | null
  ip?: string | null
  user_agent?: string | null
  duration_ms?: number | null
  created_at: IsoDateTime
}

/** `ApplicationLogResponse`. */
export interface ApplicationLog {
  id: EntityId
  trace_id?: string | null
  level: string
  logger_name?: string | null
  message: string
  exception_type?: string | null
  metadata?: Record<string, unknown> | null
  created_at: IsoDateTime
}

/** Any row returned by the unified `/admin/logs/{log_type}` endpoint. */
export type AnyLogRow =
  | AuditLog
  | SecurityLog
  | OperationLog
  | AccessLog
  | ApplicationLog

/** `TraceResponse`. */
export interface TraceDetail {
  trace_id: string
  audit_logs?: AuditLog[]
  security_logs?: SecurityLog[]
  operation_logs?: OperationLog[]
  access_logs?: AccessLog[]
}

/** `LogsSummaryResponse`. */
export interface LogsSummary {
  audit?: number
  security?: number
  operation?: number
  access?: number
  application?: number
}

/** Query parameters of `GET /admin/audit/logs`. */
export interface AuditLogQuery {
  action?: string
  operator_id?: EntityId
  resource_type?: string
  resource_id?: string
  result?: string
  start?: IsoDateTime
  end?: IsoDateTime
  page?: number
  page_size?: number
}

/** Query parameters of `GET /admin/security/logs`. */
export interface SecurityLogQuery {
  event_type?: string
  user_id?: EntityId
  result?: string
  start?: IsoDateTime
  end?: IsoDateTime
  page?: number
  page_size?: number
}

/** Query parameters of `GET /admin/operation/logs`. */
export interface OperationLogQuery {
  operation?: string
  operator_id?: EntityId
  resource_type?: string
  result?: string
  start?: IsoDateTime
  end?: IsoDateTime
  page?: number
  page_size?: number
}

/** Query parameters of `GET /admin/access/logs`. */
export interface AccessLogQuery {
  method?: string
  path?: string
  status_code?: number
  user_id?: EntityId
  start?: IsoDateTime
  end?: IsoDateTime
  page?: number
  page_size?: number
}

/** Query parameters of `GET /admin/logs/{log_type}`. */
export interface UnifiedLogQuery {
  start?: IsoDateTime
  end?: IsoDateTime
  level?: string
  result?: string
  keyword?: string
  user_id?: EntityId
  page?: number
  page_size?: number
}
