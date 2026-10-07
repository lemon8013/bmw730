/**
 * Value sets the backend persists and returns as plain strings.
 *
 * They are declared once so no page compares against a literal that does not
 * exist in the database. The ops value sets come straight from the frozen
 * enumerations in `app/ops/<module>/schema.py`.
 */

/** Host status (`ops_host.status`). */
export const HOST_STATUS = ['ONLINE', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN'] as const
export type HostStatus = (typeof HOST_STATUS)[number]

/** Service status (`ops_service.status`). */
export const SERVICE_STATUS = ['UP', 'DOWN', 'DEGRADED', 'MAINTENANCE', 'UNKNOWN'] as const
export type ServiceStatus = (typeof SERVICE_STATUS)[number]

/** Agent status (`ops_agent.status`). */
export const AGENT_STATUS = ['ONLINE', 'OFFLINE', 'UPGRADING', 'UNKNOWN'] as const
export type AgentStatus = (typeof AGENT_STATUS)[number]

/** Alert status (`ops_alert.status`). */
export const ALERT_STATUS = [
  'TRIGGERED',
  'FIRING',
  'ACKNOWLEDGED',
  'SILENCED',
  'RESOLVED',
] as const
export type AlertStatus = (typeof ALERT_STATUS)[number]

/** Alert severity; the overview always reports these four keys. */
export const ALERT_SEVERITY = ['INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const
export type AlertSeverity = (typeof ALERT_SEVERITY)[number]

/** Comparison operator of an alert rule (`ops_alert_rule.condition`). */
export const ALERT_CONDITION = ['GT', 'GTE', 'LT', 'LTE', 'EQ', 'NE'] as const
export type AlertCondition = (typeof ALERT_CONDITION)[number]

/** Scope of an alert rule or a maintenance window. */
export const SCOPE_TYPE = ['GLOBAL', 'HOST', 'SERVICE', 'ENDPOINT'] as const
export type ScopeType = (typeof SCOPE_TYPE)[number]

/** Log streams the ops log centre can search. */
export const LOG_TYPE = ['ACCESS', 'APPLICATION', 'SECURITY', 'OPERATION'] as const
export type LogType = (typeof LOG_TYPE)[number]

/** Default log stream, matching `DEFAULT_LOG_TYPE` on the backend. */
export const DEFAULT_LOG_TYPE: LogType = 'ACCESS'

/** Job run status (`sys_job.status`). */
export const JOB_STATUS = ['PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED'] as const
export type JobStatus = (typeof JOB_STATUS)[number]

/** Statuses a manual retry is meaningful for (`RETRYABLE_STATUSES`). */
export const RETRYABLE_JOB_STATUSES: readonly string[] = ['FAILED', 'CANCELLED']

/** Statuses a manual stop is meaningful for (`STOPPABLE_STATUSES`). */
export const STOPPABLE_JOB_STATUSES: readonly string[] = ['PENDING', 'RUNNING']

/** Collector probe outcome (`status` of every degradation envelope). */
export const PROBE_STATUS = ['UP', 'UNKNOWN'] as const
export type ProbeStatus = (typeof PROBE_STATUS)[number]

/** Widget types the dashboard module accepts (`WIDGET_TYPES`). */
export const WIDGET_TYPE = [
  'STAT',
  'LINE',
  'AREA',
  'BAR',
  'TABLE',
  'GAUGE',
  'TOPN',
  'TIMELINE',
] as const
export type WidgetType = (typeof WIDGET_TYPE)[number]

/** The tag colours offered by the UI kit. */
export type TagTone = 'primary' | 'success' | 'info' | 'warning' | 'danger'

/**
 * The tag colour of every value the backend returns as a status, result,
 * severity or level.
 *
 * Declared once so a status is never rendered as bare text anywhere in the
 * console, and so the same value always gets the same colour on every page.
 */
export const STATUS_TAG_TYPE: Readonly<Record<string, TagTone>> = {
  // healthy
  ONLINE: 'success',
  UP: 'success',
  ENABLED: 'success',
  ACTIVE: 'success',
  SUCCESS: 'success',
  RESOLVED: 'success',
  NORMAL: 'success',
  // needs attention
  ACKNOWLEDGED: 'warning',
  SILENCED: 'warning',
  WARNING: 'warning',
  DEGRADED: 'warning',
  MAINTENANCE: 'warning',
  PENDING: 'warning',
  RUNNING: 'warning',
  UPGRADING: 'warning',
  TRIGGERED: 'warning',
  FIRING: 'warning',
  // broken
  OFFLINE: 'info',
  DOWN: 'danger',
  FAILED: 'danger',
  ERROR: 'danger',
  CRITICAL: 'danger',
  CANCELLED: 'danger',
  // neutral
  UNKNOWN: 'info',
  DISABLED: 'info',
  INFO: 'info',
  DRAFT: 'info',
}

/** Human readable labels for the ops value sets. */
export const STATUS_LABEL: Readonly<Record<string, string>> = {
  ONLINE: '在线',
  OFFLINE: '离线',
  UP: '正常',
  DOWN: '宕机',
  DEGRADED: '降级',
  MAINTENANCE: '维护中',
  UNKNOWN: '未知',
  UPGRADING: '升级中',
  ENABLED: '启用',
  DISABLED: '停用',
  ACTIVE: '启用',
  TRIGGERED: '已触发',
  FIRING: '告警中',
  ACKNOWLEDGED: '已认领',
  SILENCED: '已静默',
  RESOLVED: '已恢复',
  INFO: '提示',
  WARNING: '警告',
  ERROR: '错误',
  CRITICAL: '严重',
  PENDING: '待执行',
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  CANCELLED: '已取消',
  GLOBAL: '全局',
  HOST: '主机',
  SERVICE: '服务',
  ENDPOINT: '端点',
}

/** Human readable labels for the log streams. */
export const LOG_TYPE_LABEL: Readonly<Record<LogType, string>> = {
  ACCESS: '访问日志',
  APPLICATION: '应用日志',
  SECURITY: '安全日志',
  OPERATION: '操作日志',
}

/** Human readable labels for the severity set. */
export const SEVERITY_LABEL: Readonly<Record<string, string>> = STATUS_LABEL

/** Human readable labels for the job statuses. */
export const JOB_STATUS_LABEL: Readonly<Record<JobStatus, string>> = {
  PENDING: '待执行',
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  CANCELLED: '已取消',
}
