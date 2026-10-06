/**
 * Permission codes referenced by the UI.
 *
 * These are the codes the backend actually seeds (`MATRIX_PERMISSIONS` plus the
 * nine codes the controllers enforce). They exist so a template never contains a
 * permission literal; the backend still decides whether the caller holds one.
 */

export const PERMISSION = {
  // users
  userView: 'USER_VIEW',
  userCreate: 'USER_CREATE',
  userEdit: 'USER_EDIT',
  userDelete: 'USER_DELETE',
  userResetPassword: 'USER_RESET_PASSWORD',
  // departments
  departmentView: 'DEPARTMENT_VIEW',
  departmentCreate: 'DEPARTMENT_CREATE',
  departmentEdit: 'DEPARTMENT_EDIT',
  departmentDelete: 'DEPARTMENT_DELETE',
  // roles
  roleView: 'ROLE_VIEW',
  roleCreate: 'ROLE_CREATE',
  roleEdit: 'ROLE_EDIT',
  roleDelete: 'ROLE_DELETE',
  roleAssign: 'ROLE_ASSIGN',
  rolePermissionEdit: 'ROLE_PERMISSION_EDIT',
  roleInheritEdit: 'ROLE_INHERIT_EDIT',
  // permissions
  permissionView: 'PERMISSION_VIEW',
  permissionResourceEdit: 'PERMISSION_RESOURCE_EDIT',
  // configuration
  dictView: 'DICT_VIEW',
  dictEdit: 'DICT_EDIT',
  configView: 'CONFIG_VIEW',
  configEdit: 'CONFIG_EDIT',
  featureFlagView: 'FEATURE_FLAG_VIEW',
  featureFlagEdit: 'FEATURE_FLAG_EDIT',
  // logs
  auditView: 'AUDIT_VIEW',
  securityLogView: 'SECURITY_LOG_VIEW',
  operationLogView: 'OPERATION_LOG_VIEW',
  accessLogView: 'ACCESS_LOG_VIEW',
  traceView: 'TRACE_VIEW',
  // sessions
  sessionView: 'SESSION_VIEW',
  sessionRevoke: 'SESSION_REVOKE',
  // tools
  toolView: 'TOOL_VIEW',
  toolEdit: 'TOOL_EDIT',
  toolPublish: 'TOOL_PUBLISH',
  toolCategoryView: 'TOOL_CATEGORY_VIEW',
  toolCategoryEdit: 'TOOL_CATEGORY_EDIT',
  toolVersionView: 'TOOL_VERSION_VIEW',
  toolVersionEdit: 'TOOL_VERSION_EDIT',
  toolAccessEdit: 'TOOL_ACCESS_EDIT',
  toolStatView: 'TOOL_STAT_VIEW',
  toolComponentView: 'TOOL_COMPONENT_VIEW',
  toolComponentEdit: 'TOOL_COMPONENT_EDIT',
  toolManage: 'TOOL_MANAGE',
  toolAccessManage: 'TOOL_ACCESS_MANAGE',
  // analytics
  analyticsDashboardView: 'ANALYTICS_DASHBOARD_VIEW',
  analyticsView: 'ANALYTICS_VIEW',
  analyticsEventView: 'ANALYTICS_EVENT_VIEW',
  analyticsExport: 'ANALYTICS_EXPORT',
  // blog
  blogArticleReview: 'BLOG_ARTICLE_REVIEW',
  blogArticlePublish: 'BLOG_ARTICLE_PUBLISH',
  blogAuthorReview: 'BLOG_AUTHOR_REVIEW',
  blogCommentReview: 'BLOG_COMMENT_REVIEW',
  blogCategoryManage: 'BLOG_CATEGORY_MANAGE',
  // growth
  levelConfigView: 'LEVEL_CONFIG_VIEW',
  levelConfigEdit: 'LEVEL_CONFIG_EDIT',
  growthRuleView: 'GROWTH_RULE_VIEW',
  growthRuleEdit: 'GROWTH_RULE_EDIT',
  pointRuleView: 'POINT_RULE_VIEW',
  pointRuleEdit: 'POINT_RULE_EDIT',
  cosmeticView: 'COSMETIC_VIEW',
  cosmeticEdit: 'COSMETIC_EDIT',
  userGrowthAdjust: 'USER_GROWTH_ADJUST',
  userPointAdjust: 'USER_POINT_ADJUST',
  // growth: codes the operator-facing gamification surface added (matrix-extra)
  bizUserView: 'BIZ_USER_VIEW',
  taskConfigView: 'TASK_CONFIG_VIEW',
  taskConfigEdit: 'TASK_CONFIG_EDIT',
  achievementConfigView: 'ACHIEVEMENT_CONFIG_VIEW',
  // operations
  exportView: 'EXPORT_VIEW',
  exportCancel: 'EXPORT_CANCEL',
  exportManage: 'EXPORT_MANAGE',
  notificationView: 'NOTIFICATION_VIEW',
  notificationSend: 'NOTIFICATION_SEND',
  notificationManage: 'NOTIFICATION_MANAGE',
  logView: 'LOG_VIEW',
  systemFileManage: 'SYSTEM_FILE_MANAGE',
  systemJobManage: 'SYSTEM_JOB_MANAGE',
} as const

/** Page permission codes, matching the seeded `PAGE_*` nodes. */
export const PAGE_PERMISSION = {
  dashboard: 'PAGE_DASHBOARD',
  user: 'PAGE_USER',
  department: 'PAGE_DEPARTMENT',
  role: 'PAGE_ROLE',
  permission: 'PAGE_PERMISSION',
  dictionary: 'PAGE_DICT',
  config: 'PAGE_CONFIG',
  featureFlag: 'PAGE_FEATURE_FLAG',
  onlineUser: 'PAGE_ONLINE_USER',
  session: 'PAGE_SESSION',
  notification: 'PAGE_NOTIFICATION',
  auditLog: 'PAGE_AUDIT_LOG',
  accessLog: 'PAGE_ACCESS_LOG',
  securityLog: 'PAGE_SECURITY_LOG',
  operationLog: 'PAGE_OPERATION_LOG',
  applicationLog: 'PAGE_APPLICATION_LOG',
  tool: 'PAGE_TOOL',
  toolCategory: 'PAGE_TOOL_CATEGORY',
  toolVersion: 'PAGE_TOOL_VERSION',
  toolAccessPolicy: 'PAGE_TOOL_ACCESS_POLICY',
  toolStatistic: 'PAGE_TOOL_STATISTIC',
  analytics: 'PAGE_ANALYTICS',
  blogArticle: 'PAGE_BLOG_ARTICLE',
  blogArticleReview: 'PAGE_BLOG_ARTICLE_REVIEW',
  blogAuthorReview: 'PAGE_BLOG_AUTHOR_REVIEW',
  blogCategory: 'PAGE_BLOG_CATEGORY',
  blogCommentReview: 'PAGE_BLOG_COMMENT_REVIEW',
  growth: 'PAGE_GROWTH',
  points: 'PAGE_POINTS',
  level: 'PAGE_LEVEL',
  task: 'PAGE_TASK',
  achievement: 'PAGE_ACHIEVEMENT',
  cosmetic: 'PAGE_COSMETIC',
  job: 'PAGE_JOB',
  file: 'PAGE_FILE',
  export: 'PAGE_EXPORT',
} as const
