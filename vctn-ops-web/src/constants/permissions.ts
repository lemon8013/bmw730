/**
 * Permission codes referenced by the console.
 *
 * These are the codes the backend actually seeds and enforces in
 * `app/ops/<module>/router.py`. They exist so a template never contains a
 * permission literal; the backend still decides whether the caller holds one.
 */

/** Write permissions — they gate the mutating buttons. */
export const OPS_PERMISSION = {
  hostManage: 'OPS_HOST_MANAGE',
  serviceManage: 'OPS_SERVICE_MANAGE',
  alertAck: 'OPS_ALERT_ACK',
  alertSilence: 'OPS_ALERT_SILENCE',
  alertManage: 'OPS_ALERT_MANAGE',
  agentManage: 'OPS_AGENT_MANAGE',
  jobManage: 'OPS_JOB_MANAGE',
  maintenanceManage: 'OPS_MAINTENANCE_MANAGE',
  dashboardManage: 'OPS_DASHBOARD_MANAGE',
  monitorManage: 'OPS_MONITOR_MANAGE',
} as const

/** Read permissions — they gate the pages the console can offer at all. */
export const OPS_VIEW_PERMISSION = {
  dashboard: 'OPS_DASHBOARD_VIEW',
  host: 'OPS_HOST_VIEW',
  service: 'OPS_SERVICE_VIEW',
  api: 'OPS_API_VIEW',
  database: 'OPS_DATABASE_VIEW',
  redis: 'OPS_REDIS_VIEW',
  log: 'OPS_LOG_VIEW',
  monitor: 'OPS_MONITOR_VIEW',
  alert: 'OPS_ALERT_VIEW',
  agent: 'OPS_AGENT_VIEW',
  job: 'OPS_JOB_VIEW',
  report: 'OPS_REPORT_VIEW',
  audit: 'OPS_AUDIT_VIEW',
} as const

/**
 * The menu nodes this console owns.
 *
 * The permissions response carries the whole menu tree of the administrator —
 * including every `MENU_*` / `PAGE_*` node of the management platform. This set
 * is the boundary: only these codes become menu entries and routes here, and
 * everything else is dropped rather than rendered.
 */
export const OPS_MENU_ROOT = 'MENU_OPS_CONSOLE'

/** The `PAGE_OPS_*` nodes wired by this build, in menu order. */
export const OPS_PAGE_PERMISSION = {
  report: 'PAGE_OPS_REPORT',
  dashboard: 'PAGE_OPS_DASHBOARD',
  host: 'PAGE_OPS_HOST',
  service: 'PAGE_OPS_SERVICE',
  api: 'PAGE_OPS_API',
  database: 'PAGE_OPS_DATABASE',
  redis: 'PAGE_OPS_REDIS',
  log: 'PAGE_OPS_LOG',
  metric: 'PAGE_OPS_METRIC',
  event: 'PAGE_OPS_EVENT',
  alert: 'PAGE_OPS_ALERT',
  alertRule: 'PAGE_OPS_ALERT_RULE',
  notification: 'PAGE_OPS_NOTIFICATION',
  maintenance: 'PAGE_OPS_MAINTENANCE',
  agent: 'PAGE_OPS_AGENT',
  availability: 'PAGE_OPS_AVAILABILITY',
  job: 'PAGE_OPS_JOB',
  dashboardConfig: 'PAGE_OPS_DASHBOARD_CFG',
  audit: 'PAGE_OPS_AUDIT',
} as const

/** Whether a permission code belongs to this console's menu branch. */
export function isOpsMenuCode(code: string): boolean {
  return code === OPS_MENU_ROOT || code.startsWith('PAGE_OPS_')
}
