# 02 Admin API

Base: `/api/v1/admin`

> 以下接口按业务域冻结。具体字段必须与数据库/DTO一致；未冻结项见 `13-未冻结项与BLOCKER.md`。

## A. Auth

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| POST | /auth/login | Public | 校验管理员状态、密码、锁定状态；成功创建 session，失败累计失败次数并写 Security Log |
| POST | /auth/refresh | Auth | 校验 refresh token hash、session 状态和过期时间，轮换 token |
| POST | /auth/logout | Auth | 当前 session 撤销 |
| GET | /auth/me | Auth | 返回当前管理员基本信息、角色、权限摘要 |
| GET | /auth/permissions | Auth | 计算当前用户最终权限集合、页面/菜单/按钮/API/字段/数据范围 |
| POST | /auth/change-password | Auth | 校验旧密码、密码策略、历史5次，更新密码并清理/撤销要求变更状态 |
| POST | /auth/reset-password | Admin | 管理员重置目标用户密码并设置 must_change_password=true |

### login 关键规则
1. 查询用户。
2. 检查 disabled/deleted/locked。
3. 校验密码。
4. 失败：原子增加 consecutive_failure_count；达到5则锁30分钟。
5. 成功：清零失败计数，创建 session。
6. 写 Access/Security Log。
7. 产生 USER_LOGIN 行为事件。
8. 不返回密码/hash/MFA secret。

## B. Users

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /users | USER_VIEW | 按 data scope 查询 |
| POST | /users | USER_CREATE | 校验创建者 scope、部门、角色可授予范围；创建用户；must_change_password=true |
| GET | /users/{id} | USER_VIEW | scope 校验后返回详情 |
| PUT | /users/{id} | USER_EDIT | scope 校验；更新允许字段 |
| DELETE | /users/{id} | USER_DELETE | 逻辑删除；禁止删除最后可用 SUPER_ADMIN |
| POST | /users/{id}/enable | USER_EDIT | 启用 |
| POST | /users/{id}/disable | USER_EDIT | 禁用；不得造成无可用 SUPER_ADMIN |
| POST | /users/{id}/reset-password | USER_RESET_PASSWORD | 重置并强制改密 |
| GET | /users/{id}/roles | ROLE_VIEW | 返回角色 |
| PUT | /users/{id}/roles | ROLE_ASSIGN | 先验证可管理目标，再验证每个 role 是否可授予 |
| PUT | /users/{id}/department | USER_EDIT | 验证目标部门在操作者可管理范围 |
| GET | /users/{id}/sessions | SESSION_VIEW | 查看目标用户 session，必须过 data scope |
| POST | /users/{id}/force-logout | SESSION_REVOKE | SUPER_ADMIN 可处理普通用户；其他管理员仅 scope 内用户；禁止踢 SUPER_ADMIN |
| GET | /users/online | SESSION_VIEW | 查询在线 session 聚合 |

### User create 业务顺序
`load manageable department → validate roles → validate username/contact uniqueness → hash password → insert user → roles → audit → outbox`

任何 scope/role 越权都必须 Audit FAILURE。

## C. Departments

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /departments/tree | DEPARTMENT_VIEW | 返回树 |
| GET | /departments | DEPARTMENT_VIEW | 分页 |
| POST | /departments | DEPARTMENT_CREATE | 校验 parent scope，创建 |
| GET | /departments/{id} | DEPARTMENT_VIEW | scope 校验 |
| PUT | /departments/{id} | DEPARTMENT_EDIT | 防止形成循环 |
| DELETE | /departments/{id} | DEPARTMENT_DELETE | 必须无有效子部门/用户或按冻结规则处理 |
| GET | /departments/{id}/children | DEPARTMENT_VIEW | descendants |
| GET | /departments/{id}/users | USER_VIEW | scope 下用户 |

## D. Roles

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /roles | ROLE_VIEW | 查询 |
| POST | /roles | ROLE_CREATE | 创建 |
| GET | /roles/{id} | ROLE_VIEW | 详情 |
| PUT | /roles/{id} | ROLE_EDIT | 更新 |
| DELETE | /roles/{id} | ROLE_DELETE | 删除前检查绑定 |
| PUT | /roles/{id}/permissions | ROLE_PERMISSION_EDIT | 保存权限资源 |
| GET | /roles/{id}/permissions | ROLE_VIEW | 查询 |
| PUT | /roles/{id}/parents | ROLE_INHERIT_EDIT | 配置继承；SQL规则未冻结时 BLOCKER |
| GET | /roles/{id}/parents | ROLE_VIEW | 查询继承 |

## E. Permissions

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /permissions/tree | PERMISSION_VIEW | 返回 Page/Menu/Button/API/Field 资源树 |
| GET | /permissions/resources | PERMISSION_VIEW | 查询资源 |
| POST | /permissions/resources | PERMISSION_RESOURCE_EDIT | 创建资源；这是 CONFLICT-001 的冻结点 |
| PUT | /permissions/resources/{id} | PERMISSION_RESOURCE_EDIT | 更新 |
| DELETE | /permissions/resources/{id} | PERMISSION_RESOURCE_EDIT | 删除前检查引用 |

## F. Dictionary / Config / Feature Flag

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /dictionaries/types | DICT_VIEW | 查询类型 |
| POST | /dictionaries/types | DICT_EDIT | 创建 |
| PUT | /dictionaries/types/{id} | DICT_EDIT | 更新 |
| DELETE | /dictionaries/types/{id} | DICT_EDIT | 逻辑删除 |
| GET | /dictionaries/types/{id}/items | DICT_VIEW | 查询项 |
| POST | /dictionaries/types/{id}/items | DICT_EDIT | 创建项并检查同类型 value 唯一 |
| PUT | /dictionaries/items/{id} | DICT_EDIT | 更新 |
| DELETE | /dictionaries/items/{id} | DICT_EDIT | 逻辑删除 |
| GET | /config | CONFIG_VIEW | 查询非 secret 配置 |
| PUT | /config/{key} | CONFIG_EDIT | 修改并 Audit |
| GET | /feature-flags | FEATURE_FLAG_VIEW | 查询 |
| POST | /feature-flags | FEATURE_FLAG_EDIT | 创建 |
| PUT | /feature-flags/{id} | FEATURE_FLAG_EDIT | 更新策略 |
| POST | /feature-flags/{id}/enable | FEATURE_FLAG_EDIT | 启用 |
| POST | /feature-flags/{id}/disable | FEATURE_FLAG_EDIT | 禁用 |

## G. Audit / Trace

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /audit/logs | AUDIT_VIEW | 按 operator/resource/result/trace 查询 |
| GET | /audit/logs/{id} | AUDIT_VIEW | 详情 |
| GET | /traces/{trace_id} | TRACE_VIEW | 汇总 request/access/audit/application 关联记录 |
| GET | /security/logs | SECURITY_LOG_VIEW | 查询 |
| GET | /operation/logs | OPERATION_LOG_VIEW | 查询 |
| GET | /access/logs | ACCESS_LOG_VIEW | 查询 |

## H. Tools Admin

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /tools | TOOL_VIEW | 查询工具 |
| POST | /tools | TOOL_EDIT | 创建工具 |
| GET | /tools/{id} | TOOL_VIEW | 详情 |
| PUT | /tools/{id} | TOOL_EDIT | 更新 |
| DELETE | /tools/{id} | TOOL_EDIT | 逻辑删除 |
| POST | /tools/{id}/publish | TOOL_PUBLISH | DRAFT/TESTING → ACTIVE，校验版本和 registry |
| POST | /tools/{id}/disable | TOOL_PUBLISH | ACTIVE → DISABLED |
| GET | /tool-categories | TOOL_CATEGORY_VIEW | 查询 |
| POST | /tool-categories | TOOL_CATEGORY_EDIT | 创建 |
| PUT | /tool-categories/{id} | TOOL_CATEGORY_EDIT | 更新 |
| DELETE | /tool-categories/{id} | TOOL_CATEGORY_EDIT | 删除 |
| GET | /tools/{id}/versions | TOOL_VERSION_VIEW | 查询版本 |
| POST | /tools/{id}/versions | TOOL_VERSION_EDIT | 创建版本 |
| PUT | /tools/{id}/access-policy | TOOL_ACCESS_EDIT | 更新 GUEST/USER_LEVEL 策略 |
| GET | /tools/{id}/statistics | TOOL_STAT_VIEW | 查询统计 |
| GET | /tools/statistics/overview | TOOL_STAT_VIEW | 总览 |
| GET | /tools/popular | TOOL_STAT_VIEW | 热门 |
| GET | /tool-components | TOOL_COMPONENT_VIEW | Registry |
| POST | /tool-components | TOOL_COMPONENT_EDIT | 注册 component_key；禁止任意 import path |

## I. Analytics Admin

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /analytics/overview | ANALYTICS_DASHBOARD_VIEW | DAU/事件/工具/页面核心指标 |
| GET | /analytics/users | ANALYTICS_VIEW | 用户行为聚合 |
| GET | /analytics/tools | ANALYTICS_VIEW | 工具行为 |
| GET | /analytics/pages | ANALYTICS_VIEW | 页面行为 |
| GET | /analytics/events | ANALYTICS_EVENT_VIEW | 原始事件检索，敏感属性过滤 |
| GET | /analytics/funnels | ANALYTICS_VIEW | 漏斗 |
| GET | /analytics/trends | ANALYTICS_VIEW | 趋势 |
| GET | /analytics/search | ANALYTICS_VIEW | 搜索行为 |
| GET | /analytics/retention | ANALYTICS_VIEW | 留存 |
| POST | /analytics/export | ANALYTICS_EXPORT | 创建异步导出任务 |

## J. Export / Notification
| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /exports | EXPORT_VIEW | 查询导出任务 |
| GET | /exports/{id} | EXPORT_VIEW | 查询状态 |
| POST | /exports/{id}/cancel | EXPORT_CANCEL | 取消 |
| GET | /notifications | NOTIFICATION_VIEW | 管理通知 |
| POST | /notifications | NOTIFICATION_SEND | 创建/发送 |
| GET | /notifications/{id} | NOTIFICATION_VIEW | 详情 |
