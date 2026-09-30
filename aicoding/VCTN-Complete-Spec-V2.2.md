# VCTN 完整开发 SPEC V2.2

> 本文件是现有 VCTN Spec/数据库/API 文档的汇总入口。内容按现有源文件原文汇总，不擅自补齐未冻结项。
> 当前架构：双前端独立 + 单 FastAPI 模块化单体 + PostgreSQL + Redis。部署运维暂不纳入当前开发范围。

## 1. 版本与来源
- Enterprise Spec: V2.0
- Business API Spec: V2.1
- Database baseline: enterprise DDL V2.0
- Development Spec package: V1.0

## 2. 冻结原则
- Agent 必须以本目录 Spec、API、DDL 为实现依据。
- 未冻结项必须停下并标记 BLOCKER，不允许自行发挥。
- 不新增未列出的第三方依赖。
- 不引入 tenant_id。
- BIGINT ID 在 API JSON 中序列化为字符串。
- 时间统一 UTC。

## 3. Enterprise Spec V2.0
# VCTN Enterprise Complete Development Specification v2.0

## 1. Architecture

```text
D:\project\bmw730\
├── vctn-admin-web
├── vctn-tools-web
└── vctn-api
```

```text
admin.example.com -> Admin Web -> api.example.com
tools.example.com -> Tools Web -> api.example.com
```

Backend is one **FastAPI modular monolith**. Do not create separate Admin API and Platform API services. Admin and Platform communicate internally through application modules/services, not HTTP.

Modules:
- admin: users, departments, roles, permissions, audit, dictionaries, config
- platform: business users, growth, points, cosmetics, tools, blog, analytics, notifications, files, search
- shared: auth, database, redis, exceptions, tracing, logging, id, idempotency, events, jobs, security

No multi-tenancy. Do not add `tenant_id`.

---

## 2. Identity model

`sys_user` = backend administrator.
`biz_user` = platform business user shared by Tools and Blog.

Admin cannot self-register. Department administrators can create users.
Business users register through the public platform.

Anonymous user identity uses `anonymous_id`; server stores `anonymous_id_hash`. IP is for rate/risk controls only and is not the sole anonymous identity.

---

## 3. Technology baseline

### Backend
- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- Pydantic
- httpx
- ARQ
- APScheduler

### Frontend
- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Element Plus

Admin Web and Tools Web are independent applications.

---

## 4. Dependency freeze

The complete third-party list is in `DEPENDENCY-INDEX.md`.

Agent rules:
- no unlisted package;
- no replacement package;
- no duplicate ORM/HTTP/Redis/UI/task/scheduler/password/JWT library;
- lock files are the final install boundary;
- exact versions must be frozen in manifests/lock files before implementation;
- an unlisted dependency is a `DEPENDENCY-BLOCKER`.

---

## 5. Global data rules

- ID: BIGINT + Snowflake.
- JSON API BIGINT IDs: strings.
- Time: UTC.
- PostgreSQL: `TIMESTAMPTZ`.
- DB names: snake_case.
- No tenant_id.
- Repository never commits.
- Service layer owns transaction boundary.
- Cross-module side effects use Outbox.

---

## 6. API contract

Base path: `/api/v1`.

Success:
```json
{"code":0,"message":"success","data":{}}
```

Error:
```json
{"code":403001,"message":"permission denied","data":null}
```

Headers:
- Authorization
- X-Trace-ID
- X-Request-ID
- Idempotency-Key when required

Pagination, error-code catalog and Snowflake exact layout remain frozen decisions and must not be invented by Agent.

---

## 7. Error system

Exception hierarchy:
- BusinessException
- ValidationException
- AuthenticationException
- AuthorizationException
- NotFoundException
- ConflictException
- RateLimitException
- IdempotencyException
- ExternalServiceException
- SystemException

Error families:
- 400xxx validation
- 401xxx authentication
- 403xxx authorization
- 404xxx not found
- 409xxx conflict
- 422xxx business validation
- 429xxx rate limit
- 500xxx system
- 503xxx dependency

Every `PermissionDeniedError` must be recorded as Security/Audit FAILURE.

---

## 8. Authentication and password

Password requirements:
- minimum 12 characters;
- uppercase;
- lowercase;
- digit;
- special character;
- cannot reuse last 5;
- mandatory change every 90 days;
- 5 consecutive failures -> 30-minute lock;
- administrator reset -> `must_change_password=true`;
- newly created admin user -> `must_change_password=true`.

Password hashes use Argon2id through the frozen password library.
Passwords are never logged or returned.

Session records login time, last active time, IP, UA, device, expiry, revocation.
Refresh token is stored only as hash.

MFA is provider-based. TOTP is supported. MFA secret is never logged, audited, analytically collected or exposed.

---

## 9. RBAC and data permission

Permission chain:

```text
User -> Role -> Role Inheritance -> Page -> Menu -> Button -> API -> Field -> Data Scope
```

Field modes:
- VISIBLE
- HIDDEN
- READ_ONLY
- EDITABLE

Data scope:
- ALL
- DEPARTMENT
- DEPARTMENT_CHILDREN
- SELF
- CUSTOM

Multiple roles union permissions.
SUPER_ADMIN is global.
Department administrator manages own department and descendants.
Backend authorization is authoritative; frontend permissions are UX only.

Use a centralized `AuthorizationService`. Do not scatter `is_super_admin` branches throughout business code.

Known unresolved items: role inheritance SQL and CUSTOM data-scope storage. These are blockers for the affected implementation phase.

---

## 10. Admin user management

Requirements:
- create user;
- disable/enable;
- logical deletion;
- reset password;
- assign roles;
- department assignment;
- online status;
- session listing;
- force logout.

SUPER_ADMIN may force logout all normal users. Other admins may only force logout users within their management scope. Non-SUPER_ADMIN cannot kick SUPER_ADMIN. At least one usable SUPER_ADMIN must remain.

Any unauthorized department change, user creation privilege escalation or role-assignment escalation must be audited as FAILURE.

---

## 11. Dictionary / configuration / Feature Flag

Dictionary:
`sys_dict_type -> sys_dict_item`.

Configuration is separate from dictionary and secret storage.

Feature Flag is accessed through `FeatureFlagService`, not direct SQL in business modules.

Supported strategies include GLOBAL, USER, USER_LEVEL, PERCENTAGE and CONDITION. Exact condition grammar is a frozen API contract, not Agent invention.

---

## 12. Logging / audit / trace

Separate:
- Access Log: 30 days
- Security Log: 180 days
- Operation Log: 180 days
- Audit Log: 2 years
- Application Log: 30 days

Trace:
`HTTP -> Controller -> Service -> Repository -> Event -> Audit/Security`.

Required IDs:
- trace_id
- request_id

Sensitive values must be masked:
- phone example: `138****1234`
- email example: `abc***@example.com`
- token: retain only first 6 characters where policy requires tracing
- password: never record
- MFA secret: never record

---

## 13. Transactions / idempotency / concurrency

Transaction boundary = Service layer.
Repository never commits.

Idempotency uses `Idempotency-Key` for critical write operations, point/growth operations, export submission and other explicitly designated operations.

Concurrency mechanisms:
- DB unique constraints
- atomic update
- optimistic version
- `SELECT FOR UPDATE`
- Redis Lua
- idempotency

Do not use unsafe GET+SET quota increments.

---

## 14. Outbox / domain events

Business transaction and Outbox insert occur in the same DB transaction.

Example:

```text
TOOL_EXECUTION_SUCCESS
  -> tool statistics
  -> analytics
  -> growth
  -> points
  -> task/achievement
  -> notification
```

Tools/Blog must not directly update growth/point accounts. They emit business events; Growth/Point services consume them.

---

## 15. Async jobs / Scheduler

Async engine is fixed to ARQ + Redis.
Scheduler is fixed to APScheduler.

Job states:
- PENDING
- RUNNING
- SUCCESS
- FAILED
- RETRYING
- CANCELLED
- DEAD

Use async jobs for large file operations, long conversions, batch processing, analytics aggregation, exports and other explicitly asynchronous tasks.

Scheduler triggers jobs; it does not contain business execution logic.

---

## 16. Unified Business User / Growth / Points

`biz_user` is shared by Tools and Blog.

Growth value determines level.
Spendable points are separate from growth.

Accounts:
- growth account
- point account

Transactions are append-only records and account balance is transactionally maintained.

Growth events support `event_id` and `idempotency_key`.

Level changes create level history and may emit `USER_LEVEL_UP`.

Cosmetics:
- AVATAR
- AVATAR_FRAME
- CROWN
- BADGE
- TITLE
- NAME_EFFECT

Tasks and achievements are modeled but exact reward values remain business configuration, not Agent invention.

---

## 17. Tools platform

Tool lifecycle:
`DRAFT -> TESTING -> ACTIVE -> DISABLED`.

Model:
`Tool Category -> Tool -> Tool Version -> Runtime`.

Core objects:
- ToolDefinition
- ToolRegistry
- ToolProvider
- ToolRuntime
- UsageReporter

No giant `if tool == ...` implementation.

Admin chooses a registered `component_key`; Admin cannot configure arbitrary Vue import paths.

Execution modes:
- FRONTEND
- BACKEND
- ASYNC

Frontend candidates include JSON/XML/YAML/TOML/Base64/UUID/random/date/text/basic image/QR/Unicode/regex/JWT decode.
Backend candidates include HTTP/DNS/IP/third-party/server-only operations.
Async is for large or long-running jobs.

Tool usage analytics are separate from behavior analytics.

---

## 18. Guest quota / rate / concurrency

Identity:
`anonymous_id_hash`.

Quota dimensions:
- guest
- user level
- tool
- day

Rate limit dimensions:
- IP
- anonymous ID
- user ID
- API
- tool

Concurrency limit is separate from quota and rate limit.

Client-provided user_id, anonymous_id, used_count or remaining quota are never trusted.

Exact thresholds are configuration/frozen business decisions and must not be guessed.

---

## 19. Tool catalog baseline

Categories:
1. Data Formatting: JSON, XML, YAML, TOML, SQL
2. Base64/Encoding
3. ID/Random
4. Date/Time
5. Text
6. Image
7. QR/Barcode
8. URL/HTTP
9. Unicode/Character Encoding
10. Developer Tools: Regex, Hash, JWT, HTML, CSS, JavaScript

Initial examples include JSON format/validate/compress, XML format/validate, YAML/TOML, SQL formatter, Base64, UUID/ULID/NanoID/Snowflake/ObjectId, random generators, date/time/Cron, Diff/text operations, image operations, QR/barcode, URL/HTTP parsing, Unicode conversions.

---

## 20. Blog

Business user applies to become author.
Admin reviews.
Approved author can publish.

Models:
- blog_author_application
- blog_author
- blog_category
- blog_article
- blog_article_tag
- blog_article_like
- blog_article_favorite
- blog_comment
- blog_user_follow

Article workflow includes draft, review and publication states.

---

## 21. Analytics / Behavior Tracking

Analytics is a separate application module.

Business state != Audit != Application Log != Behavior Event.

Core event codes:
- PAGE_VIEW
- PAGE_LEAVE
- BUTTON_CLICK
- LINK_CLICK
- TOOL_VIEW
- TOOL_START
- TOOL_EXECUTE
- TOOL_EXECUTE_SUCCESS
- TOOL_EXECUTE_FAILURE
- TOOL_COPY
- TOOL_DOWNLOAD
- TOOL_CLEAR
- USER_REGISTER
- USER_LOGIN
- USER_LOGOUT
- USER_SEARCH
- USER_FAVORITE
- LEVEL_VIEW
- POINT_VIEW
- GROWTH_VIEW
- ARTICLE_VIEW
- ARTICLE_LIKE
- ARTICLE_FAVORITE
- ARTICLE_COMMENT
- AUTHOR_FOLLOW
- SEARCH
- SEARCH_RESULT_CLICK

Do not instrument every DOM event.

Frontend SDK:
`analytics.track(event_code, properties)`.

SDK enriches anonymous ID, user ID, session ID, page, device and app version. Events are batched.

Never collect password, token, full JWT, API key, Cookie, Authorization, raw SQL, raw user input, uploaded file content, image content or MFA secret.

Raw events are separated from aggregates.

Aggregates:
- behavior_event_daily
- behavior_user_daily
- behavior_page_daily
- behavior_tool_daily
- behavior_search_daily
- behavior_funnel

Anonymous identity merge connects pre-registration behavior to a business user after registration/login.

---

## 22. Notification

Use `NotificationService`.
Channels are provider based:
- IN_APP
- EMAIL
- SMS
- WEBHOOK

V1 may implement IN_APP first. Other provider details must not be invented.

---

## 23. File / Object Storage abstraction

Business modules use `FileService`, not direct filesystem calls.

Operations:
- upload
- download
- delete
- presign
- metadata

Storage provider is abstracted. Production object-storage deployment is deferred.

---

## 24. Search

V1 uses PostgreSQL search capabilities through `SearchService`.
Do not introduce Elasticsearch/OpenSearch before a separately frozen decision.

---

## 25. Data export

Large exports are asynchronous:
`Export Request -> sys_export_job -> Async Job -> sys_file -> Download`.

Do not generate large exports synchronously in an HTTP request.

---

## 26. Risk control

`RiskService` evaluates anonymous ID, user ID, IP, UA, device, frequency and behavior signals.

Actions:
- ALLOW
- CHALLENGE
- RATE_LIMIT
- BLOCK

V1 is rule based.

---

## 27. Frontend Admin Web

Architecture:
- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios

Stores at minimum:
- authStore
- permissionStore
- appStore
- userStore
- roleStore
- departmentStore
- toolStore
- analyticsStore

Routes and menus are dynamically generated from backend permissions.

Frontend field modes:
VISIBLE/HIDDEN/READ_ONLY/EDITABLE.

Frontend never becomes the authorization authority.

---

## 28. Frontend Tools Web

Independent Vue application.

Suggested structure:

```text
src/
├── api/
├── components/
├── layouts/
├── pages/
├── router/
├── stores/
├── tools/
│   ├── registry/
│   ├── runtime/
│   └── definitions/
├── analytics/
├── quota/
├── types/
└── utils/
```

Tool pages use a common workspace shell. Tool component owns only tool business logic; access, quota, analytics and error handling remain centralized.

---

## 29. API directory baseline

### Admin
- `/api/v1/admin/auth/*`
- `/api/v1/admin/users/*`
- `/api/v1/admin/sessions/*`
- `/api/v1/admin/departments/*`
- `/api/v1/admin/roles/*`
- `/api/v1/admin/permissions/*`
- `/api/v1/admin/dictionaries/*`
- `/api/v1/admin/config/*`
- `/api/v1/admin/audit/*`
- `/api/v1/admin/traces/*`
- `/api/v1/admin/tools/*`
- `/api/v1/admin/analytics/*`
- `/api/v1/admin/notifications/*`
- `/api/v1/admin/exports/*`

### Platform
- `/api/v1/auth/*`
- `/api/v1/users/*`
- `/api/v1/levels/*`
- `/api/v1/growth/*`
- `/api/v1/points/*`
- `/api/v1/cosmetics/*`
- `/api/v1/tools/*`
- `/api/v1/blog/*`
- `/api/v1/notifications/*`
- `/api/v1/files/*`

### Analytics
- `POST /api/v1/analytics/events`
- `GET /api/v1/admin/analytics/overview`
- `GET /api/v1/admin/analytics/users`
- `GET /api/v1/admin/analytics/tools`
- `GET /api/v1/admin/analytics/pages`
- `GET /api/v1/admin/analytics/events`
- `GET /api/v1/admin/analytics/funnels`
- `GET /api/v1/admin/analytics/trends`
- `GET /api/v1/admin/analytics/search`
- `GET /api/v1/admin/analytics/retention`

Exact DTOs, pagination and final error-code catalog must follow the existing frozen API conventions and unresolved decisions.

---

## 30. Observability at application level

Keep application-level:
- trace_id
- request_id
- structured application log
- `/health`
- `/ready`
- `/version`

Production monitoring platforms are deferred.

---

## 31. Data lifecycle

Frozen retention:
- Access Log 30 days
- Security Log 180 days
- Operation Log 180 days
- Audit Log 2 years
- Application Log 30 days

Behavior event retention requires explicit business configuration and is not guessed by Agent.

---

## 32. Database rules

Full DDL is `vctn-enterprise-ddl-v2.0.sql`.

Alembic must maintain the executable migration history.

No manual production-only schema drift is permitted during development.

Large migration operations must be reviewed separately.

---

## 33. Testing

Required:
- unit tests
- integration tests
- API contract tests
- permission tests
- data-scope tests
- security tests
- concurrency tests
- idempotency tests
- migration tests
- regression tests
- frontend component tests
- E2E tests

Critical scenarios:
- privilege escalation
- unauthorized department change
- unauthorized role assignment
- SUPER_ADMIN protection
- duplicate point reward
- concurrent point update
- guest quota bypass
- anonymous identity merge
- duplicate analytics event
- outbox retry
- job failure/retry

---

## 34. Development phases

Phase 0: Spec/dependency/DB/API freeze.
Phase 1: Project skeleton/shared infrastructure.
Phase 2: Admin user/department.
Phase 3: Role/permission/data scope.
Phase 4: Auth/session/MFA.
Phase 5: Log/audit/trace.
Phase 6: Dictionary/config/feature flag.
Phase 7: Transaction/idempotency/concurrency/rate limit.
Phase 8: Tool management/runtime.
Phase 9: Unified business user.
Phase 10: Growth/points/level/cosmetics.
Phase 11: Blog.
Phase 12: Analytics.
Phase 13: Async/outbox/notification/export.
Phase 14: Admin Web.
Phase 15: Tools Web.
Phase 16: Integration.
Phase 17: Security/permission/regression.
Phase 18: Final acceptance.

Deployment and operations are a separate post-development phase.

---

## 35. Unresolved blockers — do not invent

- DD-05 Role inheritance SQL details
- DD-07 CUSTOM data scope storage
- DD-08 log partitioning
- DD-12 complete error-code catalog
- DD-13 pagination conventions
- DD-14 exact Snowflake bit layout/worker allocation
- DD-16 existing frozen decision set
- exact MFA provider set beyond the provider interface
- exact token lifecycle/TTL
- exact Redis keys/TTL
- permission cache versioning
- point expiry
- exact level thresholds
- exact point values
- points mall
- invitation/activity systems

An affected phase must pause on these blockers.

---

## 36. Deployment / operations deferred

Not part of current development:
- Docker/Kubernetes
- CI/CD
- production Nginx
- load balancing
- production monitoring platforms
- Prometheus/Grafana/ELK/Loki/Jaeger
- DB HA/replication
- Redis Cluster
- disaster recovery
- production release/rollback
- auto scaling
- production alerting

The application must still expose health/readiness/version interfaces and preserve traceability.

---

## 37. Final acceptance definition

Project is complete only when:

```text
SPEC = FROZEN
DDL = FROZEN
API = FROZEN
DEPENDENCY = FROZEN
TEST = PASSED
SECURITY = PASSED
PERMISSION = PASSED
INTEGRATION = PASSED
VERIFICATION = PASSED
```

No undocumented dependency, schema, API, permission or architecture change may remain.

## 4. API Business Spec V2.1

### Source: 01-API总则.md

# 01 API 总则

## 1.1 统一响应

成功：
```json
{"code":0,"message":"success","data":{}}
```

失败：
```json
{"code":403001,"message":"permission denied","data":null}
```

分页统一使用当前冻结规范；若当前工程尚未冻结具体字段，Agent 必须停止于 API-CONTRACT-BLOCKER，不得自行发明。

## 1.2 Header

- Authorization: Bearer <access-token>
- X-Trace-ID
- X-Request-ID
- Idempotency-Key：仅用于标记为幂等写操作的接口。

## 1.3 Controller 规则

Controller 只负责：
- 参数解析/校验
- 身份提取
- 调用 Service
- 返回 DTO
- 统一异常转换

Controller 不允许：
- 直接操作数据库
- 自己判断角色
- 自己扣积分
- 自己写统计聚合
- 自己发送通知
- 自己提交事务

## 1.4 Service 规则

Service 负责：
- 业务规则
- 权限调用
- 数据范围
- 事务
- 幂等
- 并发控制
- Domain Event
- Outbox
- 调用 Repository

## 1.5 Repository

Repository 只负责数据访问：
- select
- insert
- update
- delete/soft delete
- aggregate query

Repository 禁止 commit/rollback。

## 1.6 事件

典型：
`TOOL_EXECUTION_SUCCESS`
`TOOL_EXECUTION_FAILURE`
`USER_REGISTER`
`USER_LOGIN`
`ARTICLE_PUBLISHED`
`ARTICLE_LIKED`
`POINT_EARNED`
`USER_LEVEL_UP`

业务模块不得直接跨模块修改其他模块的账户表。

## 1.7 敏感数据

禁止进入日志、埋点、Audit before/after、异常 message：
- password
- MFA secret
- Authorization
- Cookie
- API key
- 完整 JWT
- 原始工具输入
- 上传文件内容
- 原始 SQL

### Source: 02-Admin-API.md

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

### Source: 03-Platform-API.md

# 03 Platform API

Base: `/api/v1`

## Auth

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| POST | /auth/register | Public | 创建 biz_user、身份标识、profile；初始化成长/积分账户；写 USER_REGISTER event |
| POST | /auth/login | Public | 校验 login identity；创建 business session；写 USER_LOGIN |
| POST | /auth/refresh | Auth | 校验并轮换 refresh token |
| POST | /auth/logout | Auth | 撤销当前 session |
| GET | /auth/me | Auth | 返回当前业务用户 |
| POST | /auth/change-password | Auth | 密码策略/历史检查 |
| POST | /auth/send-verification | Public/Auth | 创建验证码请求，执行风控和频控 |
| POST | /auth/verify | Public/Auth | 校验验证码并完成对应验证动作 |

## User

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /users/me | Auth | 当前用户 profile |
| PUT | /users/me | Auth | 更新允许修改的 profile 字段 |
| GET | /users/me/sessions | Auth | 当前用户 sessions |
| POST | /users/me/sessions/{id}/revoke | Auth | 仅能撤销自己的 session |
| GET | /users/me/level | Auth | 当前等级 |
| GET | /users/me/growth | Auth | 成长值账户 |
| GET | /users/me/points | Auth | 积分余额/流水摘要 |
| GET | /users/me/cosmetics | Auth | 外观资产 |
| PUT | /users/me/equipment | Auth | 装备外观；校验 inventory |
| GET | /users/me/tasks | Auth | 当前任务 |
| GET | /users/me/achievements | Auth | 当前成就 |

## Levels / Growth / Points

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /levels | Public | 可公开等级信息 |
| GET | /levels/me | Auth | 当前等级和进度 |
| GET | /growth/me | Auth | growth account |
| GET | /growth/me/transactions | Auth | growth 流水 |
| GET | /points/me | Auth | point account |
| GET | /points/me/transactions | Auth | point 流水 |
| GET | /point-rules/public | Public | 当前对用户公开的规则 |
| GET | /cosmetics | Public/Auth | 可展示的外观 |
| GET | /cosmetics/me | Auth | 已拥有外观 |
| PUT | /cosmetics/me/equipment | Auth | 装备 |
| GET | /tasks | Auth | 可参与任务 |
| POST | /tasks/{id}/claim | Auth | 领取任务，幂等 |
| GET | /tasks/me | Auth | 我的任务 |
| GET | /achievements | Public/Auth | 成就列表 |
| GET | /achievements/me | Auth | 我的成就 |

### Source: 04-Tools-API.md

# 04 Tools API

## 用户/游客

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools | Public | 按 category/status/access 返回可见工具 |
| GET | /tools/{id} | Public | 工具详情 |
| GET | /tools/by-slug/{slug} | Public | slug 查询 |
| GET | /tool-categories | Public | 分类 |
| GET | /tools/popular | Public | 热门 |
| GET | /tools/recent | Auth | 当前用户最近使用 |
| GET | /tools/{id}/access | Public/Auth | 服务端解析 guest/user/user level，返回 allowed/quota/rate 信息 |
| POST | /tools/{id}/usage | Public/Auth | 服务端识别 subject，检查 access/quota/rate/concurrency，执行或记录使用 |

## Tool usage 业务逻辑

1. 解析 authenticated biz_user 或 anonymous_id。
2. anonymous_id 必须不可预测；服务端存 hash。
3. RiskService 检查风险。
4. AccessPolicyService 判断工具是否 ACTIVE。
5. Permission/level policy 判断是否允许。
6. Redis Lua 原子扣 quota / rate。
7. FRONTEND 工具：前端执行后仅上报 usage event，不上传输入内容。
8. BACKEND：ToolRuntime 调 Provider。
9. ASYNC：创建 job，返回 job_id。
10. 记录 tool_usage_event。
11. 写 TOOL_EXECUTE_SUCCESS/FAILURE 行为事件。
12. 根据业务事件进入 Outbox，Growth/Points 异步处理。
13. 失败必须正确回滚 quota 或按冻结的计费规则处理；该规则未冻结时标记 BLOCKER。

## Async Tool Jobs

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools/jobs/{job_id} | Auth/Public按任务策略 | 仅返回当前 subject 可见任务 |
| POST | /tools/jobs/{job_id}/cancel | Auth | 仅取消自己的可取消任务 |

## Tool search
| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools/search | Public | SearchService 查询 tool/category |

### Source: 05-Blog-API.md

# 05 Blog API

## Public/User

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /blog/categories | Public | 分类 |
| GET | /blog/articles | Public | 只返回公开发布文章 |
| GET | /blog/articles/{id} | Public | 查询文章并记录 ARTICLE_VIEW |
| GET | /blog/articles/{id}/comments | Public | 查询已发布评论 |
| POST | /blog/articles/{id}/like | Auth | 幂等点赞 |
| DELETE | /blog/articles/{id}/like | Auth | 取消点赞 |
| POST | /blog/articles/{id}/favorite | Auth | 幂等收藏 |
| DELETE | /blog/articles/{id}/favorite | Auth | 取消收藏 |
| POST | /blog/articles/{id}/comments | Auth | 创建评论，风控/敏感策略后写入 |
| DELETE | /blog/comments/{id} | Auth | 仅作者本人或管理员按权限删除 |
| POST | /blog/users/{id}/follow | Auth | 关注 |
| DELETE | /blog/users/{id}/follow | Auth | 取消关注 |
| GET | /blog/users/{id} | Public | 用户/作者公开资料 |

## Author

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| POST | /blog/author/applications | Auth | 创建作者申请，防重复 |
| GET | /blog/author/application | Auth | 查看自己的申请 |
| GET | /blog/author/me | Auth | 作者状态 |
| GET | /blog/author/articles | Auth | 自己的文章 |
| POST | /blog/author/articles | Auth(Author) | 创建草稿 |
| GET | /blog/author/articles/{id} | Auth(Author) | 仅自己可编辑 |
| PUT | /blog/author/articles/{id} | Auth(Author) | 更新草稿 |
| DELETE | /blog/author/articles/{id} | Auth(Author) | 删除草稿 |
| POST | /blog/author/articles/{id}/submit-review | Auth(Author) | DRAFT → REVIEW |
| POST | /blog/author/articles/{id}/publish | Auth(Author) | 仅按冻结审核/发布规则执行；未冻结则 BLOCKER |

## Admin Blog

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /admin/blog/author-applications | BLOG_AUTHOR_REVIEW | 查询申请 |
| GET | /admin/blog/author-applications/{id} | BLOG_AUTHOR_REVIEW | 详情 |
| POST | /admin/blog/author-applications/{id}/approve | BLOG_AUTHOR_REVIEW | 审核通过，创建/激活 blog_author |
| POST | /admin/blog/author-applications/{id}/reject | BLOG_AUTHOR_REVIEW | 拒绝并记录原因 |
| GET | /admin/blog/articles | BLOG_ARTICLE_REVIEW | 管理文章 |
| POST | /admin/blog/articles/{id}/approve | BLOG_ARTICLE_REVIEW | 审核通过 |
| POST | /admin/blog/articles/{id}/reject | BLOG_ARTICLE_REVIEW | 驳回 |
| POST | /admin/blog/articles/{id}/publish | BLOG_ARTICLE_PUBLISH | 发布 |

### Source: 06-Growth-Points-Cosmetics-API.md

# 06 Growth / Points / Cosmetics API

## Admin configuration

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /admin/levels | LEVEL_CONFIG_VIEW | 查询等级 |
| POST | /admin/levels | LEVEL_CONFIG_EDIT | 创建等级 |
| PUT | /admin/levels/{id} | LEVEL_CONFIG_EDIT | 更新阈值/展示信息 |
| DELETE | /admin/levels/{id} | LEVEL_CONFIG_EDIT | 删除前检查用户引用 |
| GET | /admin/growth-rules | GROWTH_RULE_VIEW | 查询 |
| POST | /admin/growth-rules | GROWTH_RULE_EDIT | 创建 |
| PUT | /admin/growth-rules/{id} | GROWTH_RULE_EDIT | 更新 |
| GET | /admin/point-rules | POINT_RULE_VIEW | 查询 |
| POST | /admin/point-rules | POINT_RULE_EDIT | 创建 |
| PUT | /admin/point-rules/{id} | POINT_RULE_EDIT | 更新 |
| GET | /admin/cosmetics | COSMETIC_VIEW | 查询 |
| POST | /admin/cosmetics | COSMETIC_EDIT | 创建 |
| PUT | /admin/cosmetics/{id} | COSMETIC_EDIT | 更新 |
| DELETE | /admin/cosmetics/{id} | COSMETIC_EDIT | 删除 |
| POST | /admin/users/{id}/growth-adjustments | USER_GROWTH_ADJUST | 管理员调整成长值；必须 Audit |
| POST | /admin/users/{id}/point-adjustments | USER_POINT_ADJUST | 管理员调整积分；必须 Audit |

## Internal business services

这些是 Service Contract，不暴露 HTTP：
- `GrowthService.apply_event(event)`
- `PointService.apply_event(event)`
- `LevelService.recalculate(user_id)`
- `CosmeticService.grant(user_id, cosmetic_id)`
- `TaskService.consume_event(event)`
- `AchievementService.consume_event(event)`

## 核心逻辑

`TOOL_EXECUTION_SUCCESS` 等业务事件进入 Outbox。

Growth/Point consumer：
1. 读取 event_id/idempotency_key。
2. 检查是否已经处理。
3. 查询匹配规则。
4. 计算 reward。
5. 锁定账户行。
6. 写 transaction。
7. 更新 account balance/total growth。
8. 写处理幂等记录。
9. 若跨越等级阈值，写 level_history + USER_LEVEL_UP event。

不得由 ToolService 直接修改 point/growth account。

### Source: 07-Analytics-API.md

# 07 Analytics API

## Event ingest

`POST /api/v1/analytics/events`

请求核心结构：
```json
{
  "events": [
    {
      "event_id": "string",
      "event_code": "TOOL_EXECUTE",
      "occurred_at": "UTC timestamp",
      "page_code": "tool.json-format",
      "resource_type": "TOOL",
      "resource_id": "string",
      "properties": {
        "tool_code": "json-format",
        "success": true,
        "duration_ms": 18
      }
    }
  ]
}
```

服务端不得信任 client 的：
- user_id
- anonymous_id_hash
- session ownership
- operator/admin identity

服务端自行补全 identity/context。

## Event service

`AnalyticsService.ingest(events)`
1. 验证 event_code。
2. 限制 payload 大小。
3. 删除/拒绝敏感字段。
4. 服务端补全 anonymous/user/session/page/app/device。
5. event_id 幂等。
6. 批量 insert。
7. 不同步执行大聚合。
8. 异步聚合到 daily/funnel/retention。

## Anonymous identity merge

`POST /api/v1/analytics/identity/merge`

通常由登录/注册流程内部调用，不建议开放为任意公共 API。

逻辑：
`anonymous_id_hash → biz_user_id`
必须校验当前 session 与 anonymous identity 的归属。

## Admin Analytics

| Method | Path | 权限 |
|---|---|---|
| GET | /admin/analytics/overview | ANALYTICS_DASHBOARD_VIEW |
| GET | /admin/analytics/users | ANALYTICS_VIEW |
| GET | /admin/analytics/tools | ANALYTICS_VIEW |
| GET | /admin/analytics/pages | ANALYTICS_VIEW |
| GET | /admin/analytics/events | ANALYTICS_EVENT_VIEW |
| GET | /admin/analytics/funnels | ANALYTICS_VIEW |
| GET | /admin/analytics/trends | ANALYTICS_VIEW |
| GET | /admin/analytics/search | ANALYTICS_VIEW |
| GET | /admin/analytics/retention | ANALYTICS_VIEW |
| POST | /admin/analytics/export | ANALYTICS_EXPORT |

行为埋点与 Tool Usage 必须分开存储：
`TOOL_EXECUTE → tool_usage_event + behavior_event`。

### Source: 08-System-API.md

# 08 System API

## Health / version

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /health | Public | 进程存活 |
| GET | /ready | Public | DB/Redis 等必要依赖就绪状态 |
| GET | /version | Public | 应用版本 |

## Files

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| POST | /files/presign-upload | Auth/Public按业务策略 | FileService 生成上传授权 |
| POST | /files/complete | Auth/Public按业务策略 | 校验上传完成并保存 metadata |
| GET | /files/{id} | Auth/Public按策略 | metadata |
| GET | /files/{id}/download | Auth/Public按策略 | 下载/签名 URL |
| DELETE | /files/{id} | Auth | 权限校验后删除 |

## Notifications

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /notifications | Auth | 当前用户通知 |
| POST | /notifications/{id}/read | Auth | 仅本人 |
| POST | /notifications/read-all | Auth | 全部已读 |

## Search

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /search | Public/Auth | SearchService 聚合查询；V1 使用 PostgreSQL |

## Jobs

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /jobs/{id} | Auth | 仅允许访问自己的 job |
| POST | /jobs/{id}/cancel | Auth | 仅允许取消自己的可取消 job |

### Source: 09-API业务逻辑规则.md

# 09 API → 业务逻辑统一规则

## 9.1 用户创建

```text
Controller
  ↓
UserService.create
  ↓
AuthorizationService.check_create_user
  ↓
DepartmentScopeService.validate
  ↓
RoleGrantService.validate_assignable
  ↓
PasswordService.hash
  ↓
transaction:
  sys_user
  sys_user_role
  Audit
  Outbox
```

## 9.2 权限判断

所有后台写操作：
```text
load target
→ check manageable scope
→ check action permission
→ check field permission
→ execute
```

不得：
```python
if current_user.is_super_admin:
    ...
```
作为散落式业务权限实现。

## 9.3 Audit FAILURE

以下任一情况：
- PermissionDenied
- data scope 越权
- role escalation
- department escalation
- force logout protected user
- invalid administrative operation

必须写 Security/Audit FAILURE，并带 trace_id/request_id。

## 9.4 Tool execution

```text
resolve subject
→ RiskService
→ ToolService.get_active_version
→ AccessPolicyService
→ QuotaService
→ RateLimitService
→ ConcurrencyService
→ ToolRuntime
→ UsageService
→ BehaviorAnalytics
→ Outbox
```

## 9.5 Points / Growth

禁止：
```text
ToolService → UPDATE biz_user_point_account
BlogService → UPDATE biz_user_growth_account
```

必须：
```text
ToolService
→ Outbox TOOL_EXECUTION_SUCCESS
→ Growth/Point consumer
→ account transaction
```

## 9.6 Blog publication

```text
load author
→ verify author approved
→ verify article belongs to author
→ validate article state
→ transaction:
   article status
   publication timestamp
   audit/event
→ Outbox ARTICLE_PUBLISHED
```

## 9.7 Analytics

埋点接口必须：
- 批量接收
- 事件白名单
- payload size limit
- sensitive-field filter
- event_id idempotency
- async aggregate

## 9.8 Export

```text
POST export
→ validate permission/filter
→ create export_job
→ enqueue ARQ job
→ return job_id
```

HTTP 请求不得执行大查询后同步生成大文件。

## 9.9 Concurrency

必须根据业务选择：
- unique constraint
- atomic UPDATE
- SELECT FOR UPDATE
- optimistic lock
- Redis Lua
- idempotency

不能通过应用层“先查再写”假设不存在并发。

### Source: 10-Controller-Service规范.md

# 10 Controller / Service / Repository 实现规范

目录建议：

```text
app/
  admin/
    users/
      router.py
      schemas.py
      service.py
      repository.py
      models.py
      permissions.py
    roles/
    permissions/
    ...
  platform/
    users/
    growth/
    points/
    tools/
    blog/
    analytics/
  shared/
    auth/
    authorization/
    database/
    redis/
    idempotency/
    events/
    outbox/
    jobs/
    exceptions/
    logging/
    tracing/
```

每个 HTTP API：
`router -> schema -> service -> repository`

跨模块：
`service -> domain event -> outbox -> consumer/service`

每个写 Service 必须明确：
- transaction boundary
- authorization check
- data scope
- idempotency
- concurrency
- audit
- event/outbox
- return DTO

每个接口必须存在：
- request schema
- response schema
- service method
- repository methods
- error mapping
- test case

禁止：
- router 直接 SQL
- repository commit
- Service 内部直接 import FastAPI Request 作为业务依赖
- 跨模块直接修改其他模块表
- 未注册工具 component_key
- 客户端传 user_id 决定权限

### Source: 11-权限矩阵.md

# 11 权限矩阵

## Admin

```text
AUTH_LOGIN
USER_VIEW
USER_CREATE
USER_EDIT
USER_DELETE
USER_RESET_PASSWORD
ROLE_VIEW
ROLE_CREATE
ROLE_EDIT
ROLE_DELETE
ROLE_ASSIGN
ROLE_PERMISSION_EDIT
ROLE_INHERIT_EDIT
DEPARTMENT_VIEW
DEPARTMENT_CREATE
DEPARTMENT_EDIT
DEPARTMENT_DELETE
PERMISSION_VIEW
PERMISSION_RESOURCE_EDIT
DICT_VIEW
DICT_EDIT
CONFIG_VIEW
CONFIG_EDIT
FEATURE_FLAG_VIEW
FEATURE_FLAG_EDIT
AUDIT_VIEW
SECURITY_LOG_VIEW
OPERATION_LOG_VIEW
ACCESS_LOG_VIEW
TRACE_VIEW
SESSION_VIEW
SESSION_REVOKE
TOOL_VIEW
TOOL_EDIT
TOOL_PUBLISH
TOOL_CATEGORY_VIEW
TOOL_CATEGORY_EDIT
TOOL_VERSION_VIEW
TOOL_VERSION_EDIT
TOOL_ACCESS_EDIT
TOOL_STAT_VIEW
TOOL_COMPONENT_VIEW
TOOL_COMPONENT_EDIT
ANALYTICS_DASHBOARD_VIEW
ANALYTICS_VIEW
ANALYTICS_EVENT_VIEW
ANALYTICS_EXPORT
BLOG_AUTHOR_REVIEW
BLOG_ARTICLE_REVIEW
BLOG_ARTICLE_PUBLISH
LEVEL_CONFIG_VIEW
LEVEL_CONFIG_EDIT
GROWTH_RULE_VIEW
GROWTH_RULE_EDIT
POINT_RULE_VIEW
POINT_RULE_EDIT
COSMETIC_VIEW
COSMETIC_EDIT
USER_GROWTH_ADJUST
USER_POINT_ADJUST
EXPORT_VIEW
EXPORT_CANCEL
NOTIFICATION_VIEW
NOTIFICATION_SEND
```

具体角色绑定不在本文件自行决定；必须来自冻结权限配置。

## Platform

普通业务用户通过业务身份访问自身资源。
后台管理员不得通过普通 Platform API 身份绕过 Admin 权限。

## Field/Data Scope

所有 User/Department/Role 等管理 API 必须：
1. API permission
2. field permission
3. data scope

三者全部通过才执行。

### Source: 12-接口实现验收.md

# 12 接口实现验收

## API 完整性

每一个 endpoint 必须同时具备：
- Router
- Request DTO
- Response DTO
- Service
- Repository
- Authorization
- Data Scope（适用时）
- Error Mapping
- Audit（适用时）
- Trace
- Idempotency（适用时）
- Concurrency Strategy（适用时）
- Test

## 自动检查

Agent 完成后必须检查：

```text
API Catalog endpoint count
==
implemented route count
==
service contract count
```

任何不一致：
`API-IMPLEMENTATION-BLOCKER`

## 关键测试

- 正常成功
- 参数错误
- 未登录
- 无权限
- 越权数据
- 并发
- 重复请求
- 幂等
- DB unique conflict
- Redis quota race
- Outbox retry
- async job retry
- audit failure
- sensitive data masking

## 不允许

- API 已存在但 Service 为空
- 返回 200 假装业务成功
- TODO 代替业务逻辑
- NotImplementedError
- pass
- mock 永久保留
- 用内存 dict 替代 PostgreSQL/Redis
- Agent 自行增加依赖

### Source: 13-未冻结项与BLOCKER.md

# 13 未冻结项与 BLOCKER

以下项目在正式编码前必须由项目负责人冻结；AI Agent 不得自行决定：

1. DD-05 Role Inheritance SQL 具体实现
2. DD-07 CUSTOM Data Scope 存储结构
3. DD-08 Log Partitioning
4. DD-12 Error Code 完整目录
5. DD-13 Pagination 具体字段/语义
6. DD-14 Snowflake 位布局/worker 配置
7. DD-16 既有冻结项细节
8. MFA V1 provider 与完整流程
9. Access/Refresh Token TTL
10. Redis key/TTL 最终规范
11. Permission version/cache strategy
12. Feature Flag CONDITION grammar
13. Tool quota/rate/concurrency exact thresholds
14. Quota failure rollback/billing semantics
15. Point expiry
16. Level threshold / exact point-growth values
17. Task/achievement exact reward values
18. Blog article review/publish exact state machine
19. Analytics raw event retention
20. Export max range / max rows / file format
21. File storage provider
22. Notification provider
23. Search advanced grammar
24. Rate-limit exact values
25. Idempotency TTL
26. Secret manager
27. Log partitioning

规则：
`未冻结 → BLOCKER → 停止受影响接口实现`

禁止：
`未冻结 → AI 猜测 → 写死代码`

### Source: README.md

# VCTN API + Business Logic Specification v2.1

本包用于 AI Coding Agent 直接按 API Contract 实现业务逻辑。

原则：
1. API → Controller → Service → Repository → Domain/Event 的实现链路固定。
2. 不允许 Agent 根据接口名称自行猜业务规则。
3. 未冻结的规则必须标记 BLOCKER，不得自行决定。
4. Repository 不提交事务；Service 管理事务边界。
5. 权限以后端 AuthorizationService 为最终依据。
6. 跨模块副作用通过 Outbox / Domain Event。
7. BIGINT/Snowflake 在 JSON 中统一序列化为 string。
8. 所有时间使用 UTC。
9. API Base Path：`/api/v1`。
10. 本包只覆盖开发阶段；部署/运维暂不纳入。

目录：
- 01-API总则.md
- 02-Admin-API.md
- 03-Platform-API.md
- 04-Tools-API.md
- 05-Blog-API.md
- 06-Growth-Points-Cosmetics-API.md
- 07-Analytics-API.md
- 08-System-API.md
- 09-API业务逻辑规则.md
- 10-Controller-Service规范.md
- 11-权限矩阵.md
- 12-接口实现验收.md
- 13-未冻结项与BLOCKER.md

## 5. Agent / Verification Rules
# AI Coding Agent Rules

1. 先读 Spec，再写代码。
2. 先读 Dependency Index，再安装依赖。
3. 禁止安装未列出的第三方包。
4. 禁止用同类包替换冻结包。
5. 禁止增加 tenant_id。
6. 禁止把 Admin API 和 Platform API 拆成两个服务。
7. 禁止建立第二套 Business User。
8. 禁止 Repository 自己 commit。
9. Service Layer 是事务边界。
10. 权限必须通过 AuthorizationService。
11. PermissionDenied 必须记录 Security/Audit FAILURE。
12. Tools/Blog 不得直接修改积分/成长账户。
13. 跨模块副作用优先使用 Outbox。
14. BIGINT API 必须序列化为字符串。
15. 时间统一 UTC。
16. 不得记录密码、MFA Secret、Token、API Key、Cookie、Authorization、原始用户输入、上传文件内容。
17. 不得自行决定未冻结的 MFA Provider、Token TTL、Redis key/TTL、Role Inheritance SQL、CUSTOM Data Scope 存储、日志分区、积分规则等。
18. 遇到依赖、API、DB、权限、安全、Migration 冲突必须暂停。

Blocker：
- DEPENDENCY-BLOCKER
- API-CONTRACT-BLOCKER
- DB-SCHEMA-BLOCKER
- PERMISSION-BLOCKER
- SECURITY-BLOCKER
- MIGRATION-BLOCKER
- SPEC-CONFLICT

# Verification Checklist

## Architecture
- [ ] 双前端独立
- [ ] 单 FastAPI 模块化单体
- [ ] 无 tenant_id
- [ ] sys_user 与 biz_user 分离

## Dependencies
- [ ] 依赖与清单一致
- [ ] lock 文件存在
- [ ] 无未批准第三方包
- [ ] 无重复 ORM/HTTP/Redis/UI/Task/Scheduler

## Database
- [ ] PostgreSQL DDL 可执行
- [ ] Alembic 基线一致
- [ ] Snowflake BIGINT
- [ ] FK/UNIQUE/CHECK 正确
- [ ] 软删除索引正确

## Security
- [ ] 密码策略
- [ ] 密码历史
- [ ] Session 撤销
- [ ] MFA Secret 保护
- [ ] RBAC
- [ ] Field Permission
- [ ] Data Scope
- [ ] 越权 Audit
- [ ] Rate Limit
- [ ] Idempotency

## Tools
- [ ] Registry
- [ ] Component Registry
- [ ] Runtime Mode
- [ ] Guest Anonymous ID
- [ ] Quota
- [ ] Usage Event
- [ ] Popularity

## Business User / Growth
- [ ] 注册登录
- [ ] Level
- [ ] Growth
- [ ] Points
- [ ] Cosmetics
- [ ] Tasks
- [ ] Achievements

## Blog
- [ ] Author Application
- [ ] Review
- [ ] Article
- [ ] Comment
- [ ] Like
- [ ] Favorite
- [ ] Follow
- [ ] View Count

## Analytics
- [ ] SDK
- [ ] Anonymous ID
- [ ] Identity Merge
- [ ] Batch Upload
- [ ] Privacy Filtering
- [ ] Daily Aggregation
- [ ] Funnel
- [ ] Retention

## Reliability
- [ ] Transaction Boundary
- [ ] Outbox
- [ ] Idempotency
- [ ] Concurrency
- [ ] Async Job
- [ ] Scheduler
- [ ] Notification
- [ ] Export Job

## Frontend
- [ ] Dynamic routes
- [ ] Dynamic menu
- [ ] Button permission
- [ ] Field permission
- [ ] OpenAPI generated types
- [ ] Unit
- [ ] E2E

## Deferred
- [ ] Deployment/Operations remain deferred
- [ ] No Docker/K8s/CI/CD/production monitoring added to current development scope

## 6. 当前必须暂停的未冻结项
# 13 未冻结项与 BLOCKER

以下项目在正式编码前必须由项目负责人冻结；AI Agent 不得自行决定：

1. DD-05 Role Inheritance SQL 具体实现
2. DD-07 CUSTOM Data Scope 存储结构
3. DD-08 Log Partitioning
4. DD-12 Error Code 完整目录
5. DD-13 Pagination 具体字段/语义
6. DD-14 Snowflake 位布局/worker 配置
7. DD-16 既有冻结项细节
8. MFA V1 provider 与完整流程
9. Access/Refresh Token TTL
10. Redis key/TTL 最终规范
11. Permission version/cache strategy
12. Feature Flag CONDITION grammar
13. Tool quota/rate/concurrency exact thresholds
14. Quota failure rollback/billing semantics
15. Point expiry
16. Level threshold / exact point-growth values
17. Task/achievement exact reward values
18. Blog article review/publish exact state machine
19. Analytics raw event retention
20. Export max range / max rows / file format
21. File storage provider
22. Notification provider
23. Search advanced grammar
24. Rate-limit exact values
25. Idempotency TTL
26. Secret manager
27. Log partitioning

规则：
`未冻结 → BLOCKER → 停止受影响接口实现`

禁止：
`未冻结 → AI 猜测 → 写死代码`

## 7. 开发范围声明
- 当前只做项目开发，不做 Docker/K8s/生产部署、CI/CD 部署流水线、生产备份/容灾实施。
- 应用层 health/ready/version 可保留。
- 模块化单体内部不通过 HTTP 调用自身模块。
- Admin 与 Platform 业务用户身份分离：sys_user / biz_user。
