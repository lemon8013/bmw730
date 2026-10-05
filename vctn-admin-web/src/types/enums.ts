/**
 * Value sets the backend persists and returns as plain strings.
 *
 * They are declared once so no page compares against a literal that does not
 * exist in the database.
 */

/** `sys_user.status`. */
export const USER_STATUS = ['ACTIVE', 'DISABLED', 'LOCKED'] as const
export type UserStatus = (typeof USER_STATUS)[number]

/** `sys_department.status` / `sys_role.status` / most `*.status` columns. */
export const ACTIVE_STATUS = ['ACTIVE', 'DISABLED'] as const
export type ActiveStatus = (typeof ACTIVE_STATUS)[number]

/** `sys_permission.permission_type` and `resource_type`. */
export const PERMISSION_TYPE = [
  'MENU',
  'PAGE',
  'BUTTON',
  'API',
  'FIELD',
  'DATA_SCOPE',
] as const
export type PermissionType = (typeof PERMISSION_TYPE)[number]

/** `sys_permission_field.field_mode`. */
export const FIELD_MODE = ['VISIBLE', 'HIDDEN', 'READ_ONLY', 'EDITABLE'] as const
export type FieldMode = (typeof FIELD_MODE)[number]

/** `sys_role.data_scope`. */
export const DATA_SCOPE = [
  'ALL',
  'DEPARTMENT',
  'DEPARTMENT_CHILDREN',
  'SELF',
  'CUSTOM',
] as const
export type DataScopeValue = (typeof DATA_SCOPE)[number]

/** `sys_config.value_type`. */
export const CONFIG_VALUE_TYPE = ['INT', 'BOOL', 'STRING'] as const
export type ConfigValueType = (typeof CONFIG_VALUE_TYPE)[number]

/** `sys_feature_flag.strategy`. */
export const FEATURE_FLAG_STRATEGY = [
  'GLOBAL',
  'USER',
  'USER_LEVEL',
  'PERCENTAGE',
  'CONDITION',
] as const
export type FeatureFlagStrategy = (typeof FEATURE_FLAG_STRATEGY)[number]

/** `tool.execution_mode`. */
export const TOOL_EXECUTION_MODE = ['FRONTEND', 'BACKEND', 'ASYNC'] as const
export type ToolExecutionMode = (typeof TOOL_EXECUTION_MODE)[number]

/** `tool.status`. */
export const TOOL_STATUS = ['ACTIVE', 'DRAFT', 'OFFLINE', 'DEPRECATED'] as const
export type ToolStatus = (typeof TOOL_STATUS)[number]

/** `tool_access_policy.subject_type`. */
export const TOOL_SUBJECT_TYPE = ['GUEST', 'USER'] as const
export type ToolSubjectType = (typeof TOOL_SUBJECT_TYPE)[number]

/**
 * Tool visibility levels.
 *
 * `tool_access_policy` has no `subject_id` column, so visibility can only be
 * granted to every guest or to every signed in user — never to one named user.
 */
export const TOOL_VISIBILITY = ['PUBLIC', 'REGISTERED'] as const
export type ToolVisibilityLevel = (typeof TOOL_VISIBILITY)[number]

/** `sys_job.status` / `tool` job status. */
export const JOB_STATUS = [
  'PENDING',
  'RUNNING',
  'SUCCESS',
  'FAILED',
  'RETRYING',
] as const
export type JobStatus = (typeof JOB_STATUS)[number]

/** `sys_export_job.status`. */
export const EXPORT_STATUS = [
  'PENDING',
  'PROCESSING',
  'SUCCESS',
  'FAILED',
] as const
export type ExportStatus = (typeof EXPORT_STATUS)[number]

/** Log streams the backend can query. */
export const LOG_TYPE = ['audit', 'security', 'operation', 'access', 'application'] as const
export type LogType = (typeof LOG_TYPE)[number]

/** Outcome values used by every log stream. */
export const RESULT_VALUE = ['SUCCESS', 'FAILURE'] as const
export type ResultValue = (typeof RESULT_VALUE)[number]

/** `blog_article.status`. */
export const ARTICLE_STATUS = ['DRAFT', 'PUBLISHED', 'OFFLINE'] as const
export type ArticleStatus = (typeof ARTICLE_STATUS)[number]

/** `blog_article.review_status`. */
export const REVIEW_STATUS = [
  'NOT_REQUIRED',
  'PENDING',
  'APPROVED',
  'REJECTED',
] as const
export type ReviewStatus = (typeof REVIEW_STATUS)[number]

/** Review decisions accepted by the review endpoints. */
export const REVIEW_DECISION = ['APPROVED', 'REJECTED'] as const
export type ReviewDecision = (typeof REVIEW_DECISION)[number]

/** `blog_author.status`. */
export const AUTHOR_STATUS = ['ACTIVE', 'SUSPENDED'] as const
export type AuthorStatus = (typeof AUTHOR_STATUS)[number]

/** `blog_author_application.status`. */
export const APPLICATION_STATUS = [
  'PENDING',
  'APPROVED',
  'REJECTED',
] as const
export type ApplicationStatus = (typeof APPLICATION_STATUS)[number]

/** `blog_comment.status`. */
export const COMMENT_STATUS = ['PENDING', 'APPROVED', 'REJECTED'] as const
export type CommentStatus = (typeof COMMENT_STATUS)[number]

/** `biz_cosmetic.cosmetic_type`. */
export const COSMETIC_TYPE = [
  'AVATAR',
  'AVATAR_FRAME',
  'CROWN',
  'BADGE',
  'TITLE',
  'NAME_EFFECT',
] as const
export type CosmeticType = (typeof COSMETIC_TYPE)[number]

/** `sys_notification.notification_type`. */
export const NOTIFICATION_TYPE = [
  'SYSTEM',
  'BLOG_REVIEW',
  'AUTHOR_REVIEW',
  'LEVEL_UP',
  'ACHIEVEMENT',
  'TASK_REWARD',
  'EXPORT_READY',
] as const
export type NotificationType = (typeof NOTIFICATION_TYPE)[number]

/** `sys_notification.user_type`. */
export const NOTIFICATION_USER_TYPE = ['SYS_USER', 'BIZ_USER'] as const
export type NotificationUserType = (typeof NOTIFICATION_USER_TYPE)[number]

/** `sys_file.status`. */
export const FILE_STATUS = ['ACTIVE', 'DELETED'] as const
export type FileStatus = (typeof FILE_STATUS)[number]

/** Backend event codes used by the analytics module. */
export const ANALYTICS_EVENT_CODE = [
  'TOOL_VIEW',
  'TOOL_START',
  'TOOL_EXECUTE',
  'TOOL_EXECUTE_SUCCESS',
  'TOOL_EXECUTE_FAILURE',
  'TOOL_COPY',
  'TOOL_DOWNLOAD',
  'TOOL_CLEAR',
  'PAGE_VIEW',
  'SEARCH',
] as const
export type AnalyticsEventCode = (typeof ANALYTICS_EVENT_CODE)[number]

/** Human readable labels for value sets, kept beside the value sets. */
export const STATUS_LABEL: Readonly<Record<string, string>> = {
  ACTIVE: '启用',
  DISABLED: '禁用',
  LOCKED: '锁定',
  DRAFT: '草稿',
  OFFLINE: '已下线',
  DEPRECATED: '已废弃',
  PUBLISHED: '已发布',
  PENDING: '待处理',
  PROCESSING: '处理中',
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  RETRYING: '重试中',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  SUSPENDED: '已暂停',
  NOT_REQUIRED: '无需审核',
  DELETED: '已删除',
}

/** Human readable labels for the permission resource types. */
export const PERMISSION_TYPE_LABEL: Readonly<Record<PermissionType, string>> = {
  MENU: '菜单',
  PAGE: '页面',
  BUTTON: '按钮',
  API: '接口',
  FIELD: '字段',
  DATA_SCOPE: '数据范围',
}

/** Human readable labels for the notification types. */
export const NOTIFICATION_TYPE_LABEL: Readonly<Record<NotificationType, string>> = {
  SYSTEM: '系统通知',
  BLOG_REVIEW: '文章审核',
  AUTHOR_REVIEW: '作者审核',
  LEVEL_UP: '等级提升',
  ACHIEVEMENT: '成就达成',
  TASK_REWARD: '任务奖励',
  EXPORT_READY: '导出完成',
}

/** Human readable labels for the notification recipient types. */
export const NOTIFICATION_USER_TYPE_LABEL: Readonly<Record<NotificationUserType, string>> = {
  SYS_USER: '管理员',
  BIZ_USER: '业务用户',
}

/** Human readable labels for the cosmetic types. */
export const COSMETIC_TYPE_LABEL: Readonly<Record<CosmeticType, string>> = {
  AVATAR: '头像',
  AVATAR_FRAME: '头像框',
  CROWN: '皇冠',
  BADGE: '徽章',
  TITLE: '头衔',
  NAME_EFFECT: '名字特效',
}

/** Human readable labels for the tool access policy subjects. */
export const TOOL_SUBJECT_TYPE_LABEL: Readonly<Record<ToolSubjectType, string>> = {
  GUEST: '访客',
  USER: '登录用户',
}

/** Human readable labels for the tool visibility levels. */
export const TOOL_VISIBILITY_LABEL: Readonly<Record<ToolVisibilityLevel, string>> = {
  PUBLIC: '所有人可用',
  REGISTERED: '注册用户可用',
}

/** Human readable labels for the feature flag strategies. */
export const FEATURE_FLAG_STRATEGY_LABEL: Readonly<Record<FeatureFlagStrategy, string>> = {
  GLOBAL: '全局开关',
  USER: '指定用户',
  USER_LEVEL: '按用户等级',
  PERCENTAGE: '按百分比',
  CONDITION: '按条件',
}

/** Human readable labels for the configuration value types. */
export const CONFIG_VALUE_TYPE_LABEL: Readonly<Record<ConfigValueType, string>> = {
  INT: '整数',
  BOOL: '布尔',
  STRING: '字符串',
}

/** Human readable labels for the job statuses. */
export const JOB_STATUS_LABEL: Readonly<Record<JobStatus, string>> = {
  PENDING: '待执行',
  RUNNING: '执行中',
  SUCCESS: '成功',
  FAILED: '失败',
  RETRYING: '重试中',
}

/** Human readable labels for the export statuses. */
export const EXPORT_STATUS_LABEL: Readonly<Record<ExportStatus, string>> = {
  PENDING: '待处理',
  PROCESSING: '处理中',
  SUCCESS: '已完成',
  FAILED: '失败',
}

/** Human readable labels for the log outcomes. */
export const RESULT_LABEL: Readonly<Record<ResultValue, string>> = {
  SUCCESS: '成功',
  FAILURE: '失败',
}

/** The tag colours offered by the UI kit. */
export type TagTone = 'primary' | 'success' | 'info' | 'warning' | 'danger'

/**
 * The tag colour of every value the backend returns as a status, result or
 * level.
 *
 * Declared once so a status is never rendered as bare text anywhere in the
 * console, and so the same value always gets the same colour on every page.
 */
export const STATUS_TAG_TYPE: Readonly<Record<string, TagTone>> = {
  // positive
  ACTIVE: 'success',
  ENABLED: 'success',
  SUCCESS: 'success',
  APPROVED: 'success',
  PUBLISHED: 'success',
  NORMAL: 'success',
  // in progress
  PENDING: 'warning',
  PROCESSING: 'warning',
  RUNNING: 'warning',
  RETRYING: 'warning',
  SUSPENDED: 'warning',
  // negative
  FAILED: 'danger',
  REJECTED: 'danger',
  LOCKED: 'danger',
  DISABLED: 'info',
  // neutral
  DRAFT: 'info',
  OFFLINE: 'info',
  DEPRECATED: 'info',
  NOT_REQUIRED: 'info',
  DELETED: 'info',
}

/** Human readable labels for the data scope set. */
export const DATA_SCOPE_LABEL: Readonly<Record<DataScopeValue, string>> = {
  ALL: '全部数据',
  DEPARTMENT: '本部门',
  DEPARTMENT_CHILDREN: '本部门及下级',
  SELF: '仅本人',
  CUSTOM: '自定义',
}

/** Human readable labels for the field modes. */
export const FIELD_MODE_LABEL: Readonly<Record<FieldMode, string>> = {
  VISIBLE: '可见',
  HIDDEN: '隐藏',
  READ_ONLY: '只读',
  EDITABLE: '可编辑',
}

/** Human readable labels for the tool execution modes. */
export const TOOL_MODE_LABEL: Readonly<Record<ToolExecutionMode, string>> = {
  FRONTEND: '前端执行',
  BACKEND: '后端执行',
  ASYNC: '异步执行',
}

/** Human readable labels for the log streams. */
export const LOG_TYPE_LABEL: Readonly<Record<LogType, string>> = {
  audit: '审计日志',
  security: '安全日志',
  operation: '操作日志',
  access: '访问日志',
  application: '应用日志',
}
