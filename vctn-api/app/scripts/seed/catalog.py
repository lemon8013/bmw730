"""Declarative system seed data.

Everything the seed inserts is described here as plain data with a stable
business key. Values that the Spec leaves **unfrozen** are deliberately seeded as
inert (``enabled = False`` / ``0`` / ``DISABLED``) and recorded in
``BLOCKERS.md`` instead of being invented -- see ``SEED_DATA_DESIGN.md``.

Frozen sources:
* roles / data scope ..... ``VCTN-Complete-Spec-V2.2.md`` section 10
* permission codes ....... the literal ``require_permission("...")`` call sites
* tool components ........ ``app.tools.runtime.providers.build_default_registry``
* event codes ............ ``app.shared.events.codes``
* dictionary / log types . ``VCTN-Complete-Spec-V2.2.md`` sections 11 / 12
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
DEPARTMENT_CODE: Final[str] = "SYSTEM"

DEPARTMENTS: Final[tuple[tuple[str, str, str], ...]] = (
    (DEPARTMENT_CODE, "系统管理部", "平台最高管理机构"),
)

# ---------------------------------------------------------------------------
# Roles  (spec section 10: SUPER_ADMIN is global, a department administrator
# manages its own department and its descendants)
# ---------------------------------------------------------------------------
ROLE_SUPER_ADMIN: Final[str] = "SUPER_ADMIN"
ROLE_DEPARTMENT_ADMIN: Final[str] = "DEPARTMENT_ADMIN"
ROLE_AUDITOR: Final[str] = "AUDITOR"

# (role_code, role_name, data_scope, description)
ROLES: Final[tuple[tuple[str, str, str, str], ...]] = (
    (ROLE_SUPER_ADMIN, "超级管理员", "ALL", "全局管理，拥有所有权限"),
    (ROLE_DEPARTMENT_ADMIN, "部门管理员", "DEPARTMENT_CHILDREN", "管理本部门及其下级部门"),
    (ROLE_AUDITOR, "审计员", "SELF", "只读审计角色（权限矩阵未冻结，暂不授予权限）"),
)

# ---------------------------------------------------------------------------
# Menu / page / button resource tree
# ---------------------------------------------------------------------------
# (code, name, parent_code | None, kind, sort_order)
MENU_NODES: Final[tuple[tuple[str, str, str | None, str, int], ...]] = (
    ("MENU_DASHBOARD", "仪表盘", None, "MENU", 10),
    ("PAGE_DASHBOARD", "仪表盘", "MENU_DASHBOARD", "PAGE", 11),
    ("MENU_SYSTEM", "系统管理", None, "MENU", 20),
    ("PAGE_USER", "用户管理", "MENU_SYSTEM", "PAGE", 21),
    ("PAGE_DEPARTMENT", "部门管理", "MENU_SYSTEM", "PAGE", 22),
    ("PAGE_ROLE", "角色管理", "MENU_SYSTEM", "PAGE", 23),
    ("PAGE_PERMISSION", "权限管理", "MENU_SYSTEM", "PAGE", 24),
    ("PAGE_DICT", "字典管理", "MENU_SYSTEM", "PAGE", 25),
    ("PAGE_CONFIG", "系统配置", "MENU_SYSTEM", "PAGE", 26),
    ("PAGE_FEATURE_FLAG", "功能开关", "MENU_SYSTEM", "PAGE", 27),
    ("PAGE_ONLINE_USER", "在线用户", "MENU_SYSTEM", "PAGE", 28),
    ("PAGE_SESSION", "会话管理", "MENU_SYSTEM", "PAGE", 29),
    ("PAGE_NOTIFICATION", "通知管理", "MENU_SYSTEM", "PAGE", 30),
    ("MENU_LOG", "日志中心", None, "MENU", 40),
    ("PAGE_AUDIT_LOG", "审计日志", "MENU_LOG", "PAGE", 41),
    ("PAGE_ACCESS_LOG", "访问日志", "MENU_LOG", "PAGE", 42),
    ("PAGE_SECURITY_LOG", "安全日志", "MENU_LOG", "PAGE", 43),
    ("PAGE_OPERATION_LOG", "操作日志", "MENU_LOG", "PAGE", 44),
    ("PAGE_APPLICATION_LOG", "应用日志", "MENU_LOG", "PAGE", 45),
    ("MENU_TOOL", "工具管理", None, "MENU", 50),
    ("PAGE_TOOL", "工具管理", "MENU_TOOL", "PAGE", 51),
    ("PAGE_TOOL_CATEGORY", "工具分类", "MENU_TOOL", "PAGE", 52),
    ("PAGE_TOOL_VERSION", "工具版本", "MENU_TOOL", "PAGE", 53),
    ("PAGE_TOOL_ACCESS_POLICY", "工具访问策略", "MENU_TOOL", "PAGE", 54),
    ("PAGE_TOOL_STATISTIC", "工具统计", "MENU_TOOL", "PAGE", 55),
    ("MENU_ANALYTICS", "数据分析", None, "MENU", 60),
    ("PAGE_ANALYTICS", "行为分析", "MENU_ANALYTICS", "PAGE", 61),
    ("MENU_BLOG", "内容管理", None, "MENU", 70),
    ("PAGE_BLOG_ARTICLE", "文章管理", "MENU_BLOG", "PAGE", 71),
    ("PAGE_BLOG_ARTICLE_REVIEW", "文章审核", "MENU_BLOG", "PAGE", 72),
    ("PAGE_BLOG_AUTHOR_REVIEW", "作者审核", "MENU_BLOG", "PAGE", 73),
    ("PAGE_BLOG_CATEGORY", "博客分类", "MENU_BLOG", "PAGE", 74),
    ("PAGE_BLOG_COMMENT_REVIEW", "评论审核", "MENU_BLOG", "PAGE", 75),
    ("MENU_GROWTH", "成长体系", None, "MENU", 80),
    ("PAGE_GROWTH", "成长值", "MENU_GROWTH", "PAGE", 81),
    ("PAGE_POINTS", "积分", "MENU_GROWTH", "PAGE", 82),
    ("PAGE_LEVEL", "等级", "MENU_GROWTH", "PAGE", 83),
    ("PAGE_TASK", "任务", "MENU_GROWTH", "PAGE", 84),
    ("PAGE_ACHIEVEMENT", "成就", "MENU_GROWTH", "PAGE", 85),
    ("PAGE_COSMETIC", "装扮", "MENU_GROWTH", "PAGE", 86),
    ("MENU_OPS", "运维中心", None, "MENU", 90),
    ("PAGE_JOB", "作业管理", "MENU_OPS", "PAGE", 91),
    ("PAGE_FILE", "文件管理", "MENU_OPS", "PAGE", 92),
    ("PAGE_EXPORT", "导出管理", "MENU_OPS", "PAGE", 93),
)

# (code, name, parent_page_code)
BUTTONS: Final[tuple[tuple[str, str, str], ...]] = (
    ("BTN_USER_CREATE", "新增用户", "PAGE_USER"),
    ("BTN_USER_UPDATE", "编辑用户", "PAGE_USER"),
    ("BTN_USER_DELETE", "删除用户", "PAGE_USER"),
    ("BTN_USER_ENABLE", "启用用户", "PAGE_USER"),
    ("BTN_USER_DISABLE", "禁用用户", "PAGE_USER"),
    ("BTN_USER_RESET_PASSWORD", "重置密码", "PAGE_USER"),
    ("BTN_USER_ASSIGN_ROLE", "分配角色", "PAGE_USER"),
    ("BTN_USER_FORCE_LOGOUT", "强制下线", "PAGE_USER"),
    ("BTN_DEPARTMENT_CREATE", "新增部门", "PAGE_DEPARTMENT"),
    ("BTN_DEPARTMENT_UPDATE", "编辑部门", "PAGE_DEPARTMENT"),
    ("BTN_DEPARTMENT_DELETE", "删除部门", "PAGE_DEPARTMENT"),
    ("BTN_ROLE_CREATE", "新增角色", "PAGE_ROLE"),
    ("BTN_ROLE_UPDATE", "编辑角色", "PAGE_ROLE"),
    ("BTN_ROLE_DELETE", "删除角色", "PAGE_ROLE"),
    ("BTN_ROLE_GRANT", "授予权限", "PAGE_ROLE"),
    ("BTN_ROLE_REVOKE", "回收权限", "PAGE_ROLE"),
    ("BTN_PERMISSION_ASSIGN", "分配权限资源", "PAGE_PERMISSION"),
    ("BTN_DICT_CREATE", "新增字典", "PAGE_DICT"),
    ("BTN_DICT_UPDATE", "编辑字典", "PAGE_DICT"),
    ("BTN_DICT_DELETE", "删除字典", "PAGE_DICT"),
    ("BTN_CONFIG_UPDATE", "修改配置", "PAGE_CONFIG"),
    ("BTN_FEATURE_FLAG_UPDATE", "修改开关", "PAGE_FEATURE_FLAG"),
    ("BTN_AUDIT_EXPORT", "导出审计日志", "PAGE_AUDIT_LOG"),
    ("BTN_LOG_EXPORT", "导出日志", "PAGE_ACCESS_LOG"),
    ("BTN_TOOL_CREATE", "新增工具", "PAGE_TOOL"),
    ("BTN_TOOL_UPDATE", "编辑工具", "PAGE_TOOL"),
    ("BTN_TOOL_PUBLISH", "发布工具", "PAGE_TOOL"),
    ("BTN_TOOL_UNPUBLISH", "下线工具", "PAGE_TOOL"),
    ("BTN_TOOL_POLICY_UPDATE", "修改访问策略", "PAGE_TOOL_ACCESS_POLICY"),
    ("BTN_BLOG_APPROVE", "审核通过", "PAGE_BLOG_ARTICLE_REVIEW"),
    ("BTN_BLOG_REJECT", "审核驳回", "PAGE_BLOG_ARTICLE_REVIEW"),
    ("BTN_BLOG_PUBLISH", "发布文章", "PAGE_BLOG_ARTICLE"),
    ("BTN_BLOG_UNPUBLISH", "下线文章", "PAGE_BLOG_ARTICLE"),
    ("BTN_AUTHOR_APPROVE", "通过作者申请", "PAGE_BLOG_AUTHOR_REVIEW"),
    ("BTN_AUTHOR_REJECT", "驳回作者申请", "PAGE_BLOG_AUTHOR_REVIEW"),
    ("BTN_COSMETIC_EQUIP", "装备装扮", "PAGE_COSMETIC"),
    ("BTN_COSMETIC_UNEQUIP", "卸下装扮", "PAGE_COSMETIC"),
    ("BTN_EXPORT_CREATE", "创建导出任务", "PAGE_EXPORT"),
    ("BTN_EXPORT_RETRY", "重试导出", "PAGE_EXPORT"),
    ("BTN_JOB_RETRY", "重试作业", "PAGE_JOB"),
)

# ---------------------------------------------------------------------------
# Frozen permission catalogue
# ---------------------------------------------------------------------------
# ``MATRIX_PERMISSIONS`` is the *frozen* admin permission matrix
# (``aicoding/spec/07-API业务Spec/11-权限矩阵.md``). It is the single authority
# for which permission codes exist; nothing here may be renamed or invented.
MATRIX_PERMISSIONS: Final[dict[str, str]] = {
    "AUTH_LOGIN": "管理员登录",
    "USER_VIEW": "查看用户",
    "USER_CREATE": "新增用户",
    "USER_EDIT": "编辑用户",
    "USER_DELETE": "删除用户",
    "USER_RESET_PASSWORD": "重置用户密码",
    "ROLE_VIEW": "查看角色",
    "ROLE_CREATE": "新增角色",
    "ROLE_EDIT": "编辑角色",
    "ROLE_DELETE": "删除角色",
    "ROLE_ASSIGN": "分配角色",
    "ROLE_PERMISSION_EDIT": "编辑角色权限",
    "ROLE_INHERIT_EDIT": "编辑角色继承",
    "DEPARTMENT_VIEW": "查看部门",
    "DEPARTMENT_CREATE": "新增部门",
    "DEPARTMENT_EDIT": "编辑部门",
    "DEPARTMENT_DELETE": "删除部门",
    "PERMISSION_VIEW": "查看权限",
    "PERMISSION_RESOURCE_EDIT": "编辑权限资源",
    "DICT_VIEW": "查看字典",
    "DICT_EDIT": "编辑字典",
    "CONFIG_VIEW": "查看系统配置",
    "CONFIG_EDIT": "编辑系统配置",
    "FEATURE_FLAG_VIEW": "查看功能开关",
    "FEATURE_FLAG_EDIT": "编辑功能开关",
    "AUDIT_VIEW": "查看审计日志",
    "SECURITY_LOG_VIEW": "查看安全日志",
    "OPERATION_LOG_VIEW": "查看操作日志",
    "ACCESS_LOG_VIEW": "查看访问日志",
    "TRACE_VIEW": "查看链路追踪",
    "SESSION_VIEW": "查看会话",
    "SESSION_REVOKE": "吊销会话",
    "TOOL_VIEW": "查看工具",
    "TOOL_EDIT": "编辑工具",
    "TOOL_PUBLISH": "发布/下线工具",
    "TOOL_CATEGORY_VIEW": "查看工具分类",
    "TOOL_CATEGORY_EDIT": "编辑工具分类",
    "TOOL_VERSION_VIEW": "查看工具版本",
    "TOOL_VERSION_EDIT": "编辑工具版本",
    "TOOL_ACCESS_EDIT": "编辑工具访问策略",
    "TOOL_STAT_VIEW": "查看工具统计",
    "TOOL_COMPONENT_VIEW": "查看工具组件",
    "TOOL_COMPONENT_EDIT": "编辑工具组件",
    "ANALYTICS_DASHBOARD_VIEW": "查看分析总览",
    "ANALYTICS_VIEW": "查看数据分析",
    "ANALYTICS_EVENT_VIEW": "查看原始事件",
    "ANALYTICS_EXPORT": "导出数据分析",
    "BLOG_AUTHOR_REVIEW": "审核作者",
    "BLOG_ARTICLE_REVIEW": "审核文章",
    "BLOG_ARTICLE_PUBLISH": "发布文章",
    "LEVEL_CONFIG_VIEW": "查看等级配置",
    "LEVEL_CONFIG_EDIT": "编辑等级配置",
    "GROWTH_RULE_VIEW": "查看成长规则",
    "GROWTH_RULE_EDIT": "编辑成长规则",
    "POINT_RULE_VIEW": "查看积分规则",
    "POINT_RULE_EDIT": "编辑积分规则",
    "COSMETIC_VIEW": "查看装扮",
    "COSMETIC_EDIT": "编辑装扮",
    "USER_GROWTH_ADJUST": "调整用户成长值",
    "USER_POINT_ADJUST": "调整用户积分",
    "EXPORT_VIEW": "查看导出任务",
    "EXPORT_CANCEL": "取消导出任务",
    "NOTIFICATION_VIEW": "查看通知",
    "NOTIFICATION_SEND": "发送通知",
}

# Codes that the running controllers enforce but that are **absent** from the
# frozen matrix. They are seeded so authorization cannot fail closed on an
# unknown code, and every one of them is recorded in ``BLOCKERS.md`` as an
# implementation/matrix divergence. No new code may be added here silently.
RUNTIME_EXTRA_PERMISSIONS: Final[dict[str, str]] = {
    "ACHIEVEMENT_CONFIG_VIEW": "查看成就配置（矩阵外）",
    "BIZ_USER_VIEW": "查看平台业务用户（矩阵外）",
    "BLOG_CATEGORY_MANAGE": "管理博客分类（矩阵外）",
    "BLOG_COMMENT_REVIEW": "审核评论（矩阵外）",
    "EXPORT_MANAGE": "管理导出（矩阵外）",
    "LOG_VIEW": "查看日志总览（矩阵外）",
    "NOTIFICATION_MANAGE": "管理通知（矩阵外）",
    "SYSTEM_FILE_MANAGE": "管理文件（矩阵外）",
    "SYSTEM_JOB_MANAGE": "管理系统作业（矩阵外）",
    "TASK_CONFIG_EDIT": "编辑任务配置（矩阵外）",
    "TASK_CONFIG_VIEW": "查看任务配置（矩阵外）",
    "TOOL_ACCESS_MANAGE": "管理工具访问策略（矩阵外）",
    "TOOL_MANAGE": "管理工具（矩阵外）",
}

#: Everything the seed writes as an API-type business permission.
BUSINESS_PERMISSIONS: Final[dict[str, str]] = {
    **MATRIX_PERMISSIONS,
    **RUNTIME_EXTRA_PERMISSIONS,
}

# ---------------------------------------------------------------------------
# Field permissions  (attached to a business permission code)
# ---------------------------------------------------------------------------
# password material is HIDDEN everywhere: no permission can reveal it.
FIELD_PERMISSIONS: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    "USER_VIEW": (
        ("phone", "VISIBLE"),
        ("email", "VISIBLE"),
        ("password_hash", "HIDDEN"),
        ("mfa_secret", "HIDDEN"),
    ),
    "USER_EDIT": (
        ("phone", "EDITABLE"),
        ("email", "EDITABLE"),
        ("password_hash", "HIDDEN"),
        ("mfa_secret", "HIDDEN"),
    ),
    "USER_RESET_PASSWORD": (
        ("password_hash", "HIDDEN"),
        ("mfa_secret", "HIDDEN"),
    ),
}

# ---------------------------------------------------------------------------
# Data scope resources
# ---------------------------------------------------------------------------
SCOPE_PERMISSIONS: Final[tuple[str, ...]] = (
    "SCOPE_ALL",
    "SCOPE_DEPARTMENT",
    "SCOPE_DEPARTMENT_CHILDREN",
    "SCOPE_SELF",
    "SCOPE_CUSTOM",
)

# ---------------------------------------------------------------------------
# Dictionaries
# (type_code, type_name, items[(value, label, sort_order, is_default)])
# ---------------------------------------------------------------------------
DICT_TYPES: Final[tuple[tuple[str, str, tuple[tuple[str, str, int, bool], ...]], ...]] = (
    (
        "USER_STATUS",
        "用户状态",
        (
            ("ACTIVE", "启用", 1, True),
            ("DISABLED", "禁用", 2, False),
            ("LOCKED", "锁定", 3, False),
        ),
    ),
    (
        "ROLE_STATUS",
        "角色状态",
        (("ACTIVE", "启用", 1, True), ("DISABLED", "禁用", 2, False)),
    ),
    (
        "DEPARTMENT_STATUS",
        "部门状态",
        (("ACTIVE", "启用", 1, True), ("DISABLED", "禁用", 2, False)),
    ),
    (
        "GENDER",
        "性别",
        (
            ("UNKNOWN", "未知", 1, True),
            ("MALE", "男", 2, False),
            ("FEMALE", "女", 3, False),
        ),
    ),
    (
        "AUDIT_RESULT",
        "审计结果",
        (("SUCCESS", "成功", 1, True), ("FAILURE", "失败", 2, False)),
    ),
    (
        "LOG_RESULT",
        "日志结果",
        (("SUCCESS", "成功", 1, True), ("FAILURE", "失败", 2, False)),
    ),
    (
        "LOG_LEVEL",
        "日志级别",
        (
            ("INFO", "信息", 1, True),
            ("WARN", "警告", 2, False),
            ("ERROR", "错误", 3, False),
            ("DEBUG", "调试", 4, False),
        ),
    ),
    (
        "LOG_TYPE",
        "日志类型",
        (
            ("ACCESS", "访问日志", 1, True),
            ("SECURITY", "安全日志", 2, False),
            ("OPERATION", "操作日志", 3, False),
            ("AUDIT", "审计日志", 4, False),
            ("APPLICATION", "应用日志", 5, False),
        ),
    ),
    (
        "TOOL_STATUS",
        "工具状态",
        (
            ("ACTIVE", "已上线", 1, True),
            ("DRAFT", "草稿", 2, False),
            ("OFFLINE", "已下线", 3, False),
            ("DEPRECATED", "已废弃", 4, False),
        ),
    ),
    (
        "TOOL_EXECUTION_MODE",
        "工具执行模式",
        (
            ("BACKEND", "后端执行", 1, True),
            ("FRONTEND", "前端执行", 2, False),
            ("ASYNC", "异步执行", 3, False),
        ),
    ),
    (
        "TOOL_ACCESS_LEVEL",
        "工具访问级别",
        (("PUBLIC", "公开", 1, True), ("NON_PUBLIC", "非公开", 2, False)),
    ),
    (
        "TASK_STATUS",
        "任务状态",
        (("ACTIVE", "启用", 1, True), ("DISABLED", "禁用", 2, False)),
    ),
    (
        "TASK_PROGRESS_STATUS",
        "任务进度状态",
        (
            ("IN_PROGRESS", "进行中", 1, True),
            ("COMPLETED", "已完成", 2, False),
            ("EXPIRED", "已过期", 3, False),
        ),
    ),
    (
        "ACHIEVEMENT_STATUS",
        "成就状态",
        (("ACTIVE", "启用", 1, True), ("DISABLED", "禁用", 2, False)),
    ),
    (
        "NOTIFICATION_TYPE",
        "通知类型",
        (
            ("SYSTEM", "系统通知", 1, True),
            ("BLOG_REVIEW", "文章审核", 2, False),
            ("AUTHOR_REVIEW", "作者审核", 3, False),
            ("LEVEL_UP", "等级提升", 4, False),
            ("ACHIEVEMENT", "成就达成", 5, False),
            ("TASK_REWARD", "任务奖励", 6, False),
            ("EXPORT_READY", "导出完成", 7, False),
        ),
    ),
    (
        "JOB_STATUS",
        "作业状态",
        (
            ("PENDING", "待执行", 1, True),
            ("RUNNING", "执行中", 2, False),
            ("SUCCESS", "成功", 3, False),
            ("FAILED", "失败", 4, False),
            ("RETRYING", "重试中", 5, False),
        ),
    ),
    (
        "EXPORT_TASK_STATUS",
        "导出任务状态",
        (
            ("PENDING", "待处理", 1, True),
            ("PROCESSING", "处理中", 2, False),
            ("SUCCESS", "成功", 3, False),
            ("FAILED", "失败", 4, False),
        ),
    ),
    (
        "BLOG_ARTICLE_STATUS",
        "文章状态",
        (
            ("DRAFT", "草稿", 1, True),
            ("PUBLISHED", "已发布", 2, False),
            ("OFFLINE", "已下线", 3, False),
        ),
    ),
    (
        "BLOG_REVIEW_STATUS",
        "审核状态",
        (
            ("NOT_REQUIRED", "无需审核", 1, True),
            ("PENDING", "待审核", 2, False),
            ("APPROVED", "审核通过", 3, False),
            ("REJECTED", "审核驳回", 4, False),
        ),
    ),
    (
        "BLOG_AUTHOR_STATUS",
        "作者状态",
        (("ACTIVE", "正常", 1, True), ("SUSPENDED", "已暂停", 2, False)),
    ),
    (
        "BLOG_COMMENT_STATUS",
        "评论状态",
        (
            ("PENDING", "待审核", 1, True),
            ("APPROVED", "已通过", 2, False),
            ("REJECTED", "已拒绝", 3, False),
        ),
    ),
    (
        "BLOG_CATEGORY_STATUS",
        "博客分类状态",
        (("ACTIVE", "启用", 1, True), ("DISABLED", "禁用", 2, False)),
    ),
    (
        "DATA_SCOPE",
        "数据范围",
        (
            ("ALL", "全部数据", 1, True),
            ("DEPARTMENT", "本部门", 2, False),
            ("DEPARTMENT_CHILDREN", "本部门及下级", 3, False),
            ("SELF", "仅本人", 4, False),
            ("CUSTOM", "自定义", 5, False),
        ),
    ),
    (
        "FIELD_MODE",
        "字段控制模式",
        (
            ("VISIBLE", "可见", 1, True),
            ("HIDDEN", "隐藏", 2, False),
            ("READ_ONLY", "只读", 3, False),
            ("EDITABLE", "可编辑", 4, False),
        ),
    ),
    (
        "PERMISSION_TYPE",
        "权限类型",
        (
            ("PAGE", "页面", 1, True),
            ("MENU", "菜单", 2, False),
            ("BUTTON", "按钮", 3, False),
            ("API", "接口", 4, False),
            ("FIELD", "字段", 5, False),
            ("DATA_SCOPE", "数据范围", 6, False),
        ),
    ),
    (
        "FEATURE_FLAG_STRATEGY",
        "功能开关策略",
        (
            ("GLOBAL", "全局", 1, True),
            ("USER", "按用户", 2, False),
            ("USER_LEVEL", "按等级", 3, False),
            ("PERCENTAGE", "按比例", 4, False),
            ("CONDITION", "按条件", 5, False),
        ),
    ),
    (
        "COSMETIC_TYPE",
        "装扮类型",
        (
            ("AVATAR", "头像", 1, True),
            ("AVATAR_FRAME", "头像框", 2, False),
            ("CROWN", "皇冠", 3, False),
            ("BADGE", "徽章", 4, False),
            ("TITLE", "称号", 5, False),
            ("NAME_EFFECT", "昵称特效", 6, False),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Feature flags  (the flag set is not enumerated by the Spec; only switches that
# guard an existing subsystem are seeded and the gap is recorded in BLOCKERS.md)
# ---------------------------------------------------------------------------
# (flag_key, flag_name, enabled, description)
FEATURE_FLAGS: Final[tuple[tuple[str, str, bool, str], ...]] = (
    ("TOOL_ENABLED", "工具平台开关", True, "控制工具箱模块是否对外可用"),
    ("BLOG_ENABLED", "博客模块开关", True, "控制博客模块是否对外可用"),
    ("ANALYTICS_ENABLED", "行为分析开关", True, "控制行为埋点与分析是否启用"),
    ("MFA_ENABLED", "多因素认证开关", False, "MFA Provider 未冻结，默认关闭"),
)

# ---------------------------------------------------------------------------
# Business user levels  (thresholds are unfrozen - only LV1 is seeded)
# ---------------------------------------------------------------------------
LEVELS: Final[tuple[tuple[str, str, int, int], ...]] = (
    ("LV1", "Lv.1 新手", 1, 0),
    ("LV2", "Lv.2 进阶", 2, 100),
    ("LV3", "Lv.3 熟练", 3, 300),
    ("LV4", "Lv.4 高手", 4, 1000),
    ("LV5", "Lv.5 大师", 5, 3000),
)

# ---------------------------------------------------------------------------
# Growth rules  (rule_code, rule_name, event_code, growth_points, daily_limit,
#                cooldown_seconds)
#
# The frozen DDL defines the columns but leaves the numbers to product. These
# defaults make the ladder reachable: daily login alone reaches LV2 in twenty
# days, while tool use is capped per day so it cannot be farmed in bulk.
# ---------------------------------------------------------------------------
GROWTH_RULES: Final[tuple[tuple[str, str, str, int, int | None, int | None], ...]] = (
    ("GROWTH_DAILY_LOGIN", "每日登录", "DAILY_LOGIN", 5, 1, None),
    ("GROWTH_TOOL_EXECUTION_SUCCESS", "工具执行成功", "TOOL_EXECUTION_SUCCESS", 2, 20, None),
    ("GROWTH_BLOG_ARTICLE_PUBLISHED", "发布文章", "BLOG_ARTICLE_PUBLISHED", 20, 5, None),
    ("GROWTH_BLOG_COMMENT_CREATED", "发表评论", "BLOG_COMMENT_CREATED", 3, 10, 30),
    ("GROWTH_BLOG_LIKE_RECEIVED", "获得点赞", "BLOG_LIKE_RECEIVED", 1, 50, None),
)

# ---------------------------------------------------------------------------
# Point rules  (rule_code, rule_name, event_code, points, daily_limit,
#               cooldown_seconds)
# ---------------------------------------------------------------------------
POINT_RULES: Final[tuple[tuple[str, str, str, int, int | None, int | None], ...]] = (
    ("POINT_USER_REGISTER", "注册奖励", "USER_REGISTER", 100, None, None),
    ("POINT_TOOL_EXECUTION_SUCCESS", "工具执行成功", "TOOL_EXECUTION_SUCCESS", 1, 20, None),
    ("POINT_BLOG_ARTICLE_PUBLISHED", "发布文章", "BLOG_ARTICLE_PUBLISHED", 50, 5, None),
    ("POINT_BLOG_COMMENT_CREATED", "发表评论", "BLOG_COMMENT_CREATED", 5, 10, 30),
    ("POINT_BLOG_LIKE_RECEIVED", "获得点赞", "BLOG_LIKE_RECEIVED", 2, 50, None),
)

# ---------------------------------------------------------------------------
# Cosmetics catalogue  (catalogue only - nothing is granted to a user)
# ---------------------------------------------------------------------------
COSMETICS: Final[tuple[tuple[str, str, str, int], ...]] = (
    ("COS_AVATAR_DEFAULT", "默认头像", "AVATAR", 10),
    ("COS_AVATAR_FRAME_DEFAULT", "默认头像框", "AVATAR_FRAME", 20),
    ("COS_CROWN_DEFAULT", "默认皇冠", "CROWN", 30),
    ("COS_BADGE_DEFAULT", "默认徽章", "BADGE", 40),
    ("COS_TITLE_DEFAULT", "默认称号", "TITLE", 50),
    ("COS_NAME_EFFECT_DEFAULT", "默认昵称特效", "NAME_EFFECT", 60),
)

# ---------------------------------------------------------------------------
# Tasks / achievements
#
# (task_code, task_name, task_type, conditions, reward, repeatable)
#
# ``conditions`` must carry ``event_code`` (how progress is counted) and
# ``target_count`` (when the task completes). ``reward`` feeds PointService and
# GrowthService on claim, so both numeric families are named explicitly.
# ---------------------------------------------------------------------------
TASKS: Final[tuple[tuple[str, str, str, dict[str, Any], dict[str, Any], bool], ...]] = (
    (
        "TASK_DAILY_LOGIN",
        "每日登录",
        "DAILY",
        {"event_code": "DAILY_LOGIN", "target_count": 1},
        {"points": 5, "growth_points": 5},
        True,
    ),
    (
        "TASK_FIRST_TOOL_USE",
        "首次使用工具",
        "ONE_TIME",
        {"event_code": "TOOL_EXECUTION_SUCCESS", "target_count": 1},
        {"points": 20, "growth_points": 10},
        False,
    ),
    (
        "TASK_FIRST_ARTICLE_PUBLISHED",
        "首次发布文章",
        "ONE_TIME",
        {"event_code": "BLOG_ARTICLE_PUBLISHED", "target_count": 1},
        {"points": 50, "growth_points": 30},
        False,
    ),
)

# (achievement_code, achievement_name, conditions, reward)
#
# ``conditions.count`` is the number of growth events of ``event_code`` that
# unlocks it - see ``AchievementService._condition_met``.
ACHIEVEMENTS: Final[tuple[tuple[str, str, dict[str, Any], dict[str, Any]], ...]] = (
    (
        "ACH_FIRST_LOGIN",
        "初次登录",
        {"event_code": "DAILY_LOGIN", "count": 1},
        {"points": 50},
    ),
    (
        "ACH_FIRST_TOOL_EXECUTION",
        "初次使用工具",
        {"event_code": "TOOL_EXECUTION_SUCCESS", "count": 1},
        {"points": 30},
    ),
    (
        "ACH_FIRST_ARTICLE",
        "初次发布文章",
        {"event_code": "BLOG_ARTICLE_PUBLISHED", "count": 1},
        {"points": 100},
    ),
)

# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------
# (category_code, category_name, sort_order)
TOOL_CATEGORIES: Final[tuple[tuple[str, str, int], ...]] = (
    ("DATA_FORMAT", "数据格式化", 10),
    ("ENCODING", "Base64/编码", 20),
    ("ID_RANDOM", "ID/随机", 30),
    ("DATETIME", "时间日期", 40),
    ("TEXT", "文本", 50),
    ("SECURITY", "安全/加密", 60),
    ("DEVELOPER", "开发调试", 70),
    ("UNICODE", "Unicode/字符编码", 80),
    ("ASYNC", "异步任务", 90),
)

# (code, name, slug, category_code, component_key, summary)
# Every component_key exists in app.tools.runtime.providers.build_default_registry;
# no tool references a component the backend cannot execute.
TOOLS: Final[tuple[tuple[str, str, str, str, str, str], ...]] = (
    (
        "json-format", "JSON 格式化", "json-format", "DATA_FORMAT", "json.format",
        "格式化并缩进 JSON 文本",
    ),
    (
        "json-minify", "JSON 压缩", "json-minify", "DATA_FORMAT", "json.format",
        "压缩 JSON 去掉多余空白",
    ),
    (
        "json-validate", "JSON 校验", "json-validate", "DATA_FORMAT", "json.format",
        "校验 JSON 语法是否合法",
    ),
    (
        "json-beautify", "JSON 美化", "json-beautify", "DATA_FORMAT", "json.format",
        "美化 JSON 便于阅读",
    ),
    (
        "xml-format", "XML 格式化", "xml-format", "DATA_FORMAT", "xml.format",
        "格式化 XML 文档",
    ),
    (
        "toml-parse", "TOML 解析", "toml-parse", "DATA_FORMAT", "toml.parse",
        "解析 TOML 配置文本",
    ),
    (
        "markdown-render", "Markdown 渲染", "markdown-render", "DATA_FORMAT", "markdown.render",
        "将 Markdown 渲染为安全 HTML",
    ),
    (
        "base64-encode", "Base64 编码", "base64-encode", "ENCODING", "base64.codec",
        "将文本编码为 Base64",
    ),
    (
        "base64-decode", "Base64 解码", "base64-decode", "ENCODING", "base64.codec",
        "将 Base64 解码为文本",
    ),
    (
        "url-encode", "URL 编码", "url-encode", "ENCODING", "url.codec",
        "对文本进行百分号编码",
    ),
    (
        "url-decode", "URL 解码", "url-decode", "ENCODING", "url.codec",
        "还原百分号编码文本",
    ),
    (
        "uuid-generate", "UUID 生成", "uuid-generate", "ID_RANDOM", "uuid.generate",
        "批量生成 UUID v4",
    ),
    (
        "ulid-generate", "ULID 生成", "ulid-generate", "ID_RANDOM", "ulid.generate",
        "生成字典序可排序的 ULID",
    ),
    (
        "random-string", "随机字符串", "random-string", "ID_RANDOM", "random.string",
        "按长度生成随机字符串",
    ),
    (
        "datetime-convert", "时间戳转换", "datetime-convert", "DATETIME", "datetime.convert",
        "时间戳与 ISO 8601 互转",
    ),
    (
        "text-stats", "文本统计", "text-stats", "TEXT", "text.stats",
        "统计字符、词数与行数",
    ),
    (
        "hash-digest", "哈希摘要", "hash-digest", "SECURITY", "hash.digest",
        "计算文本的哈希摘要",
    ),
    (
        "jwt-parse", "JWT 解析", "jwt-parse", "SECURITY", "jwt.parse",
        "解析 JWT 的头部与载荷",
    ),
    (
        "password-generate", "随机密码生成", "password-generate", "SECURITY",
        "password.generate",
        "按字符类别与排除规则生成高强度随机密码",
    ),
    (
        "regex-test", "正则测试", "regex-test", "DEVELOPER", "regex.test",
        "测试正则表达式匹配结果",
    ),
    (
        "frontend-echo", "前端回显", "frontend-echo", "DEVELOPER", "frontend.echo",
        "回显由前端计算的结果",
    ),
    (
        "unicode-inspect", "Unicode 查询", "unicode-inspect", "UNICODE", "unicode.inspect",
        "查看字符的码点信息",
    ),
    (
        "async-job", "异步任务示例", "async-job", "ASYNC", "async.job",
        "演示异步执行模式的任务",
    ),
)

# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------
# (category_code, category_name, sort_order)
BLOG_CATEGORIES: Final[tuple[tuple[str, str, int], ...]] = (
    ("BLOG_TECH", "技术分享", 10),
    ("BLOG_TUTORIAL", "教程指南", 20),
    ("BLOG_ANNOUNCEMENT", "平台公告", 30),
    ("BLOG_NEWS", "行业资讯", 40),
)

__all__ = [
    "ACHIEVEMENTS",
    "BLOG_CATEGORIES",
    "BUSINESS_PERMISSIONS",
    "BUTTONS",
    "COSMETICS",
    "DEPARTMENTS",
    "DEPARTMENT_CODE",
    "DICT_TYPES",
    "FEATURE_FLAGS",
    "FIELD_PERMISSIONS",
    "GROWTH_RULES",
    "LEVELS",
    "MATRIX_PERMISSIONS",
    "MENU_NODES",
    "POINT_RULES",
    "ROLES",
    "ROLE_AUDITOR",
    "ROLE_DEPARTMENT_ADMIN",
    "ROLE_SUPER_ADMIN",
    "RUNTIME_EXTRA_PERMISSIONS",
    "SCOPE_PERMISSIONS",
    "TASKS",
    "TOOL_CATEGORIES",
    "TOOLS",
]
