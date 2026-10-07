/**
 * The safe bridge between the backend menu tree and the local components.
 *
 * The backend returns menu nodes with a `permission_code` only — never a path
 * and never an import path. This table is the single, reviewable place where a
 * permission code becomes a route. Keys are hard coded, so no value coming from
 * a response can ever select a component.
 *
 * A `PAGE_OPS_*` code with no entry here is rendered by the fallback "not
 * wired" page instead of being silently dropped.
 */

import type { RouteComponent } from 'vue-router'

/** Console name shown in the document title. */
export const APP_TITLE = 'VCTN 运维监控'

/** One wired console page. */
export interface PageDefinition {
  /** `sys_permission.permission_code` of the `PAGE` node. */
  permissionCode: string
  /** Router path, absolute within the authenticated shell. */
  path: string
  /** Route name; unique and stable. */
  name: string
  /** Page title, used by the menu, the breadcrumb and the document title. */
  title: string
  /** Element Plus icon component name. */
  icon: string
  /** Lazily resolved component. The specifier is static by construction. */
  component: RouteComponent
}

function lazy(loader: () => Promise<unknown>): RouteComponent {
  return loader as RouteComponent
}

/** Every implemented page, keyed by the permission code the backend sends. */
export const OPS_PAGE_TABLE: Readonly<Record<string, PageDefinition>> = {
  PAGE_OPS_REPORT: {
    permissionCode: 'PAGE_OPS_REPORT',
    path: '/ops/reports',
    name: 'ops-reports',
    title: '运维报表',
    icon: 'DataAnalysis',
    component: lazy(() => import('@/pages/ReportsPage.vue')),
  },
  PAGE_OPS_DASHBOARD: {
    permissionCode: 'PAGE_OPS_DASHBOARD',
    path: '/ops/overview',
    name: 'ops-overview',
    title: '运维总览',
    icon: 'Odometer',
    component: lazy(() => import('@/pages/OverviewPage.vue')),
  },
  PAGE_OPS_HOST: {
    permissionCode: 'PAGE_OPS_HOST',
    path: '/ops/hosts',
    name: 'ops-hosts',
    title: '主机监控',
    icon: 'Monitor',
    component: lazy(() => import('@/pages/HostsPage.vue')),
  },
  PAGE_OPS_SERVICE: {
    permissionCode: 'PAGE_OPS_SERVICE',
    path: '/ops/services',
    name: 'ops-services',
    title: '服务监控',
    icon: 'Grid',
    component: lazy(() => import('@/pages/ServicesPage.vue')),
  },
  PAGE_OPS_API: {
    permissionCode: 'PAGE_OPS_API',
    path: '/ops/apis',
    name: 'ops-apis',
    title: 'API 监控',
    icon: 'Connection',
    component: lazy(() => import('@/pages/ApiListPage.vue')),
  },
  PAGE_OPS_DATABASE: {
    permissionCode: 'PAGE_OPS_DATABASE',
    path: '/ops/database',
    name: 'ops-database',
    title: 'PostgreSQL',
    icon: 'Coin',
    component: lazy(() => import('@/pages/DatabasePage.vue')),
  },
  PAGE_OPS_REDIS: {
    permissionCode: 'PAGE_OPS_REDIS',
    path: '/ops/redis',
    name: 'ops-redis',
    title: 'Redis',
    icon: 'Files',
    component: lazy(() => import('@/pages/RedisPage.vue')),
  },
  PAGE_OPS_LOG: {
    permissionCode: 'PAGE_OPS_LOG',
    path: '/ops/logs',
    name: 'ops-logs',
    title: '日志中心',
    icon: 'Document',
    component: lazy(() => import('@/pages/LogsPage.vue')),
  },
  PAGE_OPS_METRIC: {
    permissionCode: 'PAGE_OPS_METRIC',
    path: '/ops/metrics',
    name: 'ops-metrics',
    title: '指标中心',
    icon: 'DataLine',
    component: lazy(() => import('@/pages/MetricsPage.vue')),
  },
  PAGE_OPS_EVENT: {
    permissionCode: 'PAGE_OPS_EVENT',
    path: '/ops/events',
    name: 'ops-events',
    title: '事件中心',
    icon: 'Bell',
    component: lazy(() => import('@/pages/EventsPage.vue')),
  },
  PAGE_OPS_ALERT: {
    permissionCode: 'PAGE_OPS_ALERT',
    path: '/ops/alerts',
    name: 'ops-alerts',
    title: '告警中心',
    icon: 'Warning',
    component: lazy(() => import('@/pages/AlertsPage.vue')),
  },
  PAGE_OPS_ALERT_RULE: {
    permissionCode: 'PAGE_OPS_ALERT_RULE',
    path: '/ops/alert-rules',
    name: 'ops-alert-rules',
    title: '告警规则',
    icon: 'Finished',
    component: lazy(() => import('@/pages/AlertRulesPage.vue')),
  },
  PAGE_OPS_NOTIFICATION: {
    permissionCode: 'PAGE_OPS_NOTIFICATION',
    path: '/ops/notifications',
    name: 'ops-notifications',
    title: '通知中心',
    icon: 'Message',
    component: lazy(() => import('@/pages/NotificationsPage.vue')),
  },
  PAGE_OPS_MAINTENANCE: {
    permissionCode: 'PAGE_OPS_MAINTENANCE',
    path: '/ops/maintenance',
    name: 'ops-maintenance',
    title: '维护窗口',
    icon: 'Clock',
    component: lazy(() => import('@/pages/MaintenancePage.vue')),
  },
  PAGE_OPS_AGENT: {
    permissionCode: 'PAGE_OPS_AGENT',
    path: '/ops/agents',
    name: 'ops-agents',
    title: 'Agent',
    icon: 'Cpu',
    component: lazy(() => import('@/pages/AgentsPage.vue')),
  },
  PAGE_OPS_AVAILABILITY: {
    permissionCode: 'PAGE_OPS_AVAILABILITY',
    path: '/ops/availability',
    name: 'ops-availability',
    title: '可用性',
    icon: 'View',
    component: lazy(() => import('@/pages/AvailabilityPage.vue')),
  },
  PAGE_OPS_JOB: {
    permissionCode: 'PAGE_OPS_JOB',
    path: '/ops/jobs',
    name: 'ops-jobs',
    title: '作业监控',
    icon: 'Timer',
    component: lazy(() => import('@/pages/JobsPage.vue')),
  },
  PAGE_OPS_DASHBOARD_CFG: {
    permissionCode: 'PAGE_OPS_DASHBOARD_CFG',
    path: '/ops/dashboards',
    name: 'ops-dashboards',
    title: '仪表盘配置',
    icon: 'Odometer',
    component: lazy(() => import('@/pages/DashboardsPage.vue')),
  },
  PAGE_OPS_AUDIT: {
    permissionCode: 'PAGE_OPS_AUDIT',
    path: '/ops/audit',
    name: 'ops-audit',
    title: '运维审计',
    icon: 'Tickets',
    component: lazy(() => import('@/pages/OpsAuditPage.vue')),
  },
}

/** Every permission code this build can turn into a route. */
export const WIRED_PAGE_CODES: readonly string[] = Object.keys(OPS_PAGE_TABLE)

/** Fallback page used when a menu entry has no wired implementation. */
export const unwiredPage: PageDefinition = {
  permissionCode: '__UNWIRED__ANY',
  path: '/unwired',
  name: 'ops-unwired',
  title: '页面未接入',
  icon: 'WarningFilled',
  component: lazy(() => import('@/pages/errors/UnwiredPage.vue')),
}

/** Resolve a menu permission code to a page definition. */
export function resolvePage(permissionCode: string): PageDefinition | null {
  return OPS_PAGE_TABLE[permissionCode] ?? null
}
