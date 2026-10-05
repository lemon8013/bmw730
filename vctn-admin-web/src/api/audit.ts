/** Audit, security, operation and access log queries (`app/admin/audit`). */

import { get } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  AccessLog,
  AccessLogQuery,
  AuditLog,
  AuditLogQuery,
  OperationLog,
  OperationLogQuery,
  SecurityLog,
  SecurityLogQuery,
} from '@/types/audit'

/** `GET /admin/audit/logs` */
export function listAuditLogs(query: AuditLogQuery = {}): Promise<Page<AuditLog>> {
  return get<Page<AuditLog>>('/admin/audit/logs', { params: query })
}

/** `GET /admin/audit/logs/{log_id}` */
export function getAuditLog(logId: string): Promise<AuditLog> {
  return get<AuditLog>(`/admin/audit/logs/${logId}`)
}

/** `GET /admin/security/logs` */
export function listSecurityLogs(query: SecurityLogQuery = {}): Promise<Page<SecurityLog>> {
  return get<Page<SecurityLog>>('/admin/security/logs', { params: query })
}

/** `GET /admin/operation/logs` */
export function listOperationLogs(query: OperationLogQuery = {}): Promise<Page<OperationLog>> {
  return get<Page<OperationLog>>('/admin/operation/logs', { params: query })
}

/** `GET /admin/access/logs` */
export function listAccessLogs(query: AccessLogQuery = {}): Promise<Page<AccessLog>> {
  return get<Page<AccessLog>>('/admin/access/logs', { params: query })
}
