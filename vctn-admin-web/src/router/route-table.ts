/**
 * The safe bridge between the backend menu tree and the local components.
 *
 * The backend returns menu nodes with a `permission_code` only — never a path
 * and never an import path. This table is the single, reviewable place where a
 * permission code becomes a route. Keys are hard coded, so no value coming from
 * a response can ever select a component.
 *
 * A page whose permission code is missing here is rendered by the fallback
 * "not wired" page instead of being silently dropped.
 */

import type { RouteComponent } from 'vue-router'

/** One wired administrative page. */
export interface PageDefinition {
  /** `sys_permission.permission_code` of the `PAGE` node. */
  permissionCode: string
  /** Router path, absolute within the authenticated shell. */
  path: string
  /** Route name; unique and stable. */
  name: string
  /** Page title, used by the breadcrumb and the document title. */
  title: string
  /** Element Plus icon component name. */
  icon: string
  /** Lazily resolved component. The specifier is static by construction. */
  component: RouteComponent
  /** Permission required to open the page; defaults to `permissionCode`. */
  guardPermission?: string
}

/** Fallback page for a menu entry this build does not implement. */
export const UNWIRED_PERMISSION_PREFIX = '__UNWIRED__'

function lazy(loader: () => Promise<unknown>): RouteComponent {
  return loader as RouteComponent
}

/** Every implemented page, keyed by the permission code the backend sends. */
export const PAGE_TABLE: Readonly<Record<string, PageDefinition>> = {
  PAGE_DASHBOARD: {
    permissionCode: 'PAGE_DASHBOARD',
    path: '/dashboard',
    name: 'dashboard',
    title: '仪表盘',
    icon: 'Odometer',
    component: lazy(() => import('@/pages/dashboard/DashboardPage.vue')),
  },
  PAGE_USER: {
    permissionCode: 'PAGE_USER',
    path: '/system/users',
    name: 'user-list',
    title: '用户管理',
    icon: 'User',
    component: lazy(() => import('@/pages/users/UserListPage.vue')),
  },
  PAGE_DEPARTMENT: {
    permissionCode: 'PAGE_DEPARTMENT',
    path: '/system/departments',
    name: 'department-tree',
    title: '部门管理',
    icon: 'OfficeBuilding',
    component: lazy(() => import('@/pages/departments/DepartmentPage.vue')),
  },
  PAGE_ROLE: {
    permissionCode: 'PAGE_ROLE',
    path: '/system/roles',
    name: 'role-list',
    title: '角色管理',
    icon: 'Avatar',
    component: lazy(() => import('@/pages/roles/RoleListPage.vue')),
  },
  PAGE_PERMISSION: {
    permissionCode: 'PAGE_PERMISSION',
    path: '/system/permissions',
    name: 'permission-resources',
    title: '权限管理',
    icon: 'Key',
    component: lazy(() => import('@/pages/permissions/PermissionPage.vue')),
  },
  PAGE_DICT: {
    permissionCode: 'PAGE_DICT',
    path: '/system/dictionaries',
    name: 'dictionary-list',
    title: '字典管理',
    icon: 'Collection',
    component: lazy(() => import('@/pages/dictionaries/DictionaryPage.vue')),
  },
  PAGE_CONFIG: {
    permissionCode: 'PAGE_CONFIG',
    path: '/system/config',
    name: 'config-list',
    title: '系统配置',
    icon: 'Setting',
    component: lazy(() => import('@/pages/config/ConfigPage.vue')),
  },
  PAGE_FEATURE_FLAG: {
    permissionCode: 'PAGE_FEATURE_FLAG',
    path: '/system/feature-flags',
    name: 'feature-flag-list',
    title: '功能开关',
    icon: 'Switch',
    component: lazy(() => import('@/pages/feature-flags/FeatureFlagPage.vue')),
  },
  PAGE_ONLINE_USER: {
    permissionCode: 'PAGE_ONLINE_USER',
    path: '/sessions/online',
    name: 'online-user-list',
    title: '在线用户',
    icon: 'Connection',
    component: lazy(() => import('@/pages/sessions/OnlineUserPage.vue')),
  },
  PAGE_SESSION: {
    permissionCode: 'PAGE_SESSION',
    path: '/sessions',
    name: 'session-list',
    title: '会话管理',
    icon: 'Monitor',
    component: lazy(() => import('@/pages/sessions/SessionPage.vue')),
  },
  PAGE_NOTIFICATION: {
    permissionCode: 'PAGE_NOTIFICATION',
    path: '/system/notifications',
    name: 'notification-list',
    title: '通知管理',
    icon: 'Bell',
    component: lazy(() => import('@/pages/notifications/NotificationPage.vue')),
  },
  PAGE_AUDIT_LOG: {
    permissionCode: 'PAGE_AUDIT_LOG',
    path: '/logs/audit',
    name: 'audit-log-list',
    title: '审计日志',
    icon: 'Document',
    component: lazy(() => import('@/pages/logs/AuditLogPage.vue')),
  },
  PAGE_ACCESS_LOG: {
    permissionCode: 'PAGE_ACCESS_LOG',
    path: '/logs/access',
    name: 'access-log-list',
    title: '访问日志',
    icon: 'Tickets',
    component: lazy(() => import('@/pages/logs/AccessLogPage.vue')),
  },
  PAGE_SECURITY_LOG: {
    permissionCode: 'PAGE_SECURITY_LOG',
    path: '/logs/security',
    name: 'security-log-list',
    title: '安全日志',
    icon: 'Lock',
    component: lazy(() => import('@/pages/logs/SecurityLogPage.vue')),
  },
  PAGE_OPERATION_LOG: {
    permissionCode: 'PAGE_OPERATION_LOG',
    path: '/logs/operation',
    name: 'operation-log-list',
    title: '操作日志',
    icon: 'EditPen',
    component: lazy(() => import('@/pages/logs/OperationLogPage.vue')),
  },
  PAGE_APPLICATION_LOG: {
    permissionCode: 'PAGE_APPLICATION_LOG',
    path: '/logs/application',
    name: 'application-log-list',
    title: '应用日志',
    icon: 'Cpu',
    component: lazy(() => import('@/pages/logs/ApplicationLogPage.vue')),
  },
  PAGE_TOOL: {
    permissionCode: 'PAGE_TOOL',
    path: '/tools',
    name: 'tool-list',
    title: '工具管理',
    icon: 'Suitcase',
    component: lazy(() => import('@/pages/tools/ToolListPage.vue')),
  },
  PAGE_TOOL_CATEGORY: {
    permissionCode: 'PAGE_TOOL_CATEGORY',
    path: '/tools/categories',
    name: 'tool-category-list',
    title: '工具分类',
    icon: 'Grid',
    component: lazy(() => import('@/pages/tools/ToolCategoryPage.vue')),
  },
  PAGE_TOOL_VERSION: {
    permissionCode: 'PAGE_TOOL_VERSION',
    path: '/tools/versions',
    name: 'tool-version-list',
    title: '工具版本',
    icon: 'Files',
    component: lazy(() => import('@/pages/tools/ToolVersionPage.vue')),
  },
  PAGE_TOOL_ACCESS_POLICY: {
    permissionCode: 'PAGE_TOOL_ACCESS_POLICY',
    path: '/tools/access-policies',
    name: 'tool-access-policy-list',
    title: '工具访问策略',
    icon: 'Unlock',
    component: lazy(() => import('@/pages/tools/ToolAccessPolicyPage.vue')),
  },
  PAGE_TOOL_STATISTIC: {
    permissionCode: 'PAGE_TOOL_STATISTIC',
    path: '/tools/statistics',
    name: 'tool-statistics',
    title: '工具统计',
    icon: 'TrendCharts',
    component: lazy(() => import('@/pages/tools/ToolStatisticsPage.vue')),
  },
  PAGE_ANALYTICS: {
    permissionCode: 'PAGE_ANALYTICS',
    path: '/analytics',
    name: 'analytics-overview',
    title: '行为分析',
    icon: 'DataAnalysis',
    component: lazy(() => import('@/pages/analytics/AnalyticsPage.vue')),
  },
  PAGE_BLOG_ARTICLE: {
    permissionCode: 'PAGE_BLOG_ARTICLE',
    path: '/blog/articles',
    name: 'article-list',
    title: '文章管理',
    icon: 'Notebook',
    component: lazy(() => import('@/pages/blog/ArticleListPage.vue')),
  },
  PAGE_BLOG_ARTICLE_REVIEW: {
    permissionCode: 'PAGE_BLOG_ARTICLE_REVIEW',
    path: '/blog/review',
    name: 'article-review',
    title: '文章审核',
    icon: 'Finished',
    component: lazy(() => import('@/pages/blog/ArticleReviewPage.vue')),
  },
  PAGE_BLOG_AUTHOR_REVIEW: {
    permissionCode: 'PAGE_BLOG_AUTHOR_REVIEW',
    path: '/blog/authors',
    name: 'author-review',
    title: '作者审核',
    icon: 'Medal',
    component: lazy(() => import('@/pages/blog/AuthorPage.vue')),
  },
  PAGE_BLOG_CATEGORY: {
    permissionCode: 'PAGE_BLOG_CATEGORY',
    path: '/blog/categories',
    name: 'blog-category-list',
    title: '博客分类',
    icon: 'FolderOpened',
    component: lazy(() => import('@/pages/blog/BlogCategoryPage.vue')),
  },
  PAGE_BLOG_COMMENT_REVIEW: {
    permissionCode: 'PAGE_BLOG_COMMENT_REVIEW',
    path: '/blog/comments',
    name: 'comment-review',
    title: '评论审核',
    icon: 'ChatDotRound',
    component: lazy(() => import('@/pages/blog/CommentReviewPage.vue')),
  },
  PAGE_GROWTH: {
    permissionCode: 'PAGE_GROWTH',
    path: '/growth',
    name: 'growth-overview',
    title: '成长值',
    icon: 'TrendCharts',
    component: lazy(() => import('@/pages/growth/GrowthPage.vue')),
  },
  PAGE_POINTS: {
    permissionCode: 'PAGE_POINTS',
    path: '/growth/points',
    name: 'point-overview',
    title: '积分',
    icon: 'Coin',
    component: lazy(() => import('@/pages/points/PointPage.vue')),
  },
  PAGE_LEVEL: {
    permissionCode: 'PAGE_LEVEL',
    path: '/growth/levels',
    name: 'level-list',
    title: '等级',
    icon: 'Medal',
    component: lazy(() => import('@/pages/levels/LevelPage.vue')),
  },
  PAGE_TASK: {
    permissionCode: 'PAGE_TASK',
    path: '/growth/tasks',
    name: 'task-list',
    title: '任务',
    icon: 'List',
    component: lazy(() => import('@/pages/tasks/TaskPage.vue')),
  },
  PAGE_ACHIEVEMENT: {
    permissionCode: 'PAGE_ACHIEVEMENT',
    path: '/growth/achievements',
    name: 'achievement-list',
    title: '成就',
    icon: 'Trophy',
    component: lazy(() => import('@/pages/achievements/AchievementPage.vue')),
  },
  PAGE_COSMETIC: {
    permissionCode: 'PAGE_COSMETIC',
    path: '/growth/cosmetics',
    name: 'cosmetic-list',
    title: '装扮',
    icon: 'Brush',
    component: lazy(() => import('@/pages/cosmetics/CosmeticPage.vue')),
  },
  PAGE_JOB: {
    permissionCode: 'PAGE_JOB',
    path: '/ops/jobs',
    name: 'job-list',
    title: '作业管理',
    icon: 'Timer',
    component: lazy(() => import('@/pages/jobs/JobPage.vue')),
  },
  PAGE_FILE: {
    permissionCode: 'PAGE_FILE',
    path: '/ops/files',
    name: 'file-list',
    title: '文件管理',
    icon: 'Folder',
    component: lazy(() => import('@/pages/files/FilePage.vue')),
  },
  PAGE_EXPORT: {
    permissionCode: 'PAGE_EXPORT',
    path: '/ops/exports',
    name: 'export-list',
    title: '导出管理',
    icon: 'Download',
    component: lazy(() => import('@/pages/exports/ExportPage.vue')),
  },
}

/** Every permission code this build can turn into a route. */
export const WIRED_PAGE_CODES: readonly string[] = Object.keys(PAGE_TABLE)

/** Fallback page used when a menu entry has no wired implementation. */
export const unwiredPage: PageDefinition = {
  permissionCode: `${UNWIRED_PERMISSION_PREFIX}ANY`,
  path: '/unwired',
  name: 'unwired-page',
  title: '页面未接入',
  icon: 'Warning',
  component: lazy(() => import('@/pages/errors/UnwiredPage.vue')),
}

/** Resolve a menu permission code to a page definition. */
export function resolvePage(permissionCode: string): PageDefinition | null {
  return PAGE_TABLE[permissionCode] ?? null
}
