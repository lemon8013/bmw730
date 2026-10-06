# VCTN 项目长期记忆

## 项目定位
VCTN：**双前端 + 单 FastAPI 模块化单体**。
- `vctn-api`：唯一后端（FastAPI），业务前缀 `/api/v1`，系统探针 `/health` `/ready` `/version` 在根路径。
- `vctn-admin-web`：管理平台前端（端口 5173）。
- `vctn-tools-web`：Tools 平台前端（端口 5174）。
- 两前端工程完全独立，不互相 import；共享的是后端 API Contract。
- 禁令：不建 `admin-api`/`platform-api`/`tools-api`/`blog-api`，不拆微服务，模块间不得 HTTP 互调。

## 关键约定
- **项目根目录 = `F:\project\bmw730`**（负责人 Phase 0 决策；Spec 原文写 `D:\project\bmw730`）。
- Spec 唯一来源：`aicoding/`（`VCTN-Complete-Spec-V2.2.md`、`spec/`、`sql/vctn-enterprise-ddl-v2.0.sql`）。
- 依赖名单唯一来源：`aicoding/spec/08-EnterpriseBaseline/DEPENDENCY-INDEX.md`。清单外的包 = DEPENDENCY-BLOCKER。
  - SQLAlchemy 异步必须用 `sqlalchemy[asyncio]`（greenlet）。
- 禁止 `tenant_id`（单组织模型）；ID = BIGINT + Snowflake，API JSON 序列化为 string；时间统一 UTC、API 用 ISO 8601。
- Service 是事务边界，Repository 不 commit；授权必须经 AuthorizationService，后端是最终权威。
- 敏感信息（密码 / MFA Secret / Token / API Key / Cookie / Authorization / 原始用户输入 / 上传文件内容）禁止进日志。
- 禁止 `pass` / `TODO` / `NotImplementedError` / fake response / mock 业务数据。
- **后端配置唯一来源（负责人硬性要求）：`vctn-api/app/core/config.py::Settings` + `vctn-api/.env`。禁止在任何其他后端代码里硬编码配置。**
  - 新增任何可调参数：先在 `Settings` 加字段，再同步写入 `vctn-api/.env.example`（`tests/unit/test_config_surface.py` 会强制两者字段集合一致，且不得有未知键）。
  - `.env` 由负责人创建、已被 gitignore，禁止提交；`.env.example` 中 `DATABASE_URL`/`REDIS_URL` 必须留空。
  - `alembic.ini` 的 `sqlalchemy.url` 必须留空，由 `migrations/env.py` 从 Settings 注入，禁止写凭据。
  - 真实环境变量优先级高于 `.env`。
- **数据库结构的唯一来源：`aicoding/sql/vctn-enterprise-ddl-v2.0.sql`（79 张表）。** Model 必须 100% 对齐 DDL，禁止自行增删改字段/表名/约束/索引，禁止加 `tenant_id`。

## 已冻结 vs 待冻结（节选）
- 已冻结：ToolRegistry、ToolRuntime、component_key、FRONTEND/BACKEND/ASYNC、sys_user 与 biz_user 分离。
- 未冻结（遇到必须停下报 BLOCKER，禁止自行发明）：MFA Provider、Access/Refresh Token TTL、Redis key/TTL、权限缓存版本方案、Role Inheritance SQL、CUSTOM Data Scope 存储、日志分区、**UI 组件库**、最终 Tool API DTO、Error Code 完整目录（DD-12）、Pagination 语义（DD-13）、Snowflake 位布局（DD-14）、积分/等级/任务具体数值。

## 工程状态
- Phase 0 已完成并停止（2026-09-30）。提交：`b4ab41c`（工程骨架）、`38b746b`（验证报告）。
- 报告：`PHASE-0-VERIFICATION-REPORT.md`。
- 后端 venv：`vctn-api/.venv`（Python 3.13.14）；依赖锁：`vctn-api/requirements.lock.txt`。
- 待关闭：PG/Redis 连接信息（BLOCKER-1）；Spec 回写根目录与版本清单（BLOCKER-2）。

## 工具可见性两档 + 管理员侧用量统计（2026-10-05，勿回退）
- 可见性只有两档：`PUBLIC`（所有人可用）/ `REGISTERED`（注册用户可用），写入 `tool_access_policy`
  的 GUEST + USER 两行。表无 `subject_id`，**做不到指定用户/角色可见**（B-35 未决）。
- 默认可见性 = `Settings.TOOL_DEFAULT_VISIBILITY`（默认 `PUBLIC`，已同步 `.env.example`）。
- 管理入口：工具列表页 `/tools` 的「可见性」列行内下拉 → `PUT /admin/tools/visibility/{tool_id}`
  （TOOL_ACCESS_MANAGE）；列表读 `GET /admin/tools/visibility`（TOOL_VIEW）。
- **执行与读侧都必须过滤**：`ToolAccessService.enforce_quota()` 开头拦可见性；目录
  `list_tools/search/get_by_slug/get_tool/popular` 按 `OptionalPrincipal 为空 = 游客` 过滤。
  只改一处会漏：改 resolve 不改目录 → 游客看得到但不能用；反过来更糟。
- 管理员侧用量：`GET /admin/tools/usage[?days]`、`GET /admin/tools/usage/daily?tool_id&days`
  （TOOL_STAT_VIEW）。**直接聚合 `tool_usage_event`**，不读 `tool_usage_daily` /
  `tool_popularity_daily`（后者恒为 0，B-36）。
- 平台侧 `/tools/usage/*`、`/tools/statistics/*` 读接口全要业务用户身份，**Operator 必 401**，
  管理端页面不要碰它们（B-33 同类问题）。
- FastAPI 陷阱：`/admin/tools/visibility`、`/admin/tools/usage` 等字面量路由必须注册在
  `/admin/tools/{tool_id}` 之前。
- 执行端点真实路径：`/api/v1/tools/runtime/execute/{tool_id}`。

## tools-web 工具门户（2026-10-04 实现完成）
- 6 条路由全部落地：`/` `/category/:slug`（=category_code）`/search` `/popular` `/recent` `/tool/:slug`。
- component_key 白名单 = `src/tools/definitions/index.ts`（18 个），**必须与
  `vctn-api/app/tools/runtime/providers.py::build_default_registry` 保持同步**；
  守门测试 `vctn-tools-web/tests/definitions.spec.ts` 会比对两侧 key 集合。
- **新增工具的三处必改**：① providers.py 加 Provider 并注册到 `build_default_registry`
  ② `app/scripts/seed/catalog.py::TOOLS` 加条目（指定分类）③ 前端 definitions 加表单 +
  测试 key 集合。改完必须重跑 seed（`VCTN_SEED_ADMIN_PASSWORD` 要显式给）才能进目录。
- 全站返回首页：`AppLayout` 非首页显示「返回首页」按钮 + `AppBreadcrumb` 面包屑
  （首级恒为首页），5 个二级页面都已接入。
- 工作区表单由 ToolFieldDescriptor 驱动；FRONTEND 本地算 result 再 POST；
  ASYNC 拿 job_id 轮询 `/tools/jobs/{id}`（终态 SUCCESS/FAILED/CANCELLED）。
- 最近使用走 localStorage；服务端 `/tools/recent` 需业务用户登录（**2026-10-06 已可用**）。
- 工具目录/分类/搜索/热门/执行匿名即可用；无需 token。
- tools-web 浏览器验证脚本：`vctn-tools-web/scripts/browser-verify.sh`（无需 token）。
- 后端曾有 bug：usage record 与 repository 重复传 `id` 导致执行 500，已修（勿回退：
  id 由 `ToolUsageRepository.add_event` 统一生成）。

## tools-web 登录 / 注册（2026-10-06 补齐，勿回退）
- tools-web 是**匿名优先**门户：不登录也能用全部工具，登录只解锁 `/tools/recent`、
  `/tools/usage/*` 这类需要业务身份的端点。不要加全局路由守卫把游客挡在外面。
- 会话：`src/api/credentials.ts`（sessionStorage，key 前缀 **`vctn.tools.`**，与 admin-web 的
  `vctn.admin.` 分开）、`src/api/session.ts`（单飞刷新 + `onSessionExpired` 回调）、
  `src/stores/auth.ts`、`src/pages/LoginPage.vue`、`src/components/UserMenu.vue`。
- `apiBaseUrl` 在 `src/api/endpoint.ts`（不是 client.ts），为了断开 client ↔ session 循环依赖。
- `/login` 路由在 `AppLayout` **之外**（不带目录导航），支持 `?redirect=` 同站回跳；
  注册接口不签发会话，所以注册成功后要**再调一次登录**。
- 后端注册**必须**填 email 或 phone 至少一个；密码策略是 **≥12 位 + 大小写 + 数字 + 特殊字符**
  （违反返回 422001，`data` 是具体问题列表，`ApiEnvelopeError.details` 已保留它）。
- 后端两个既有坑已修（见 2026-10-06 日志）：`RateLimitService` 遇 Redis 故障要 fail-open；
  `BizUserSession` 在 `app.platform.users.model` **不在** `auth.model`。

## 环境坑
- **启动服务（2026-10-03 验证）**
  - Git Bash 里 `nohup ... &` / `&` 起的进程会在父任务结束时被回收，**不可靠**。
  - `Start-Process` 被安全策略拦截（`F:\project\bmw730\scripts\start-all.ps1` 因此不可用）。
  - **可靠方式：Bash 工具 `run_in_background=true`，命令本身就是前台长驻进程**，三个服务
    各起一个后台任务（api:8000 / admin-web:5173 / tools-web:5174）。
  - 本机探测必须加 `--noproxy '*'`（否则被 http_proxy 吞掉），且用 `localhost` 而非
    `127.0.0.1`（Vite 只监听 IPv6）。
- `aicoding/spec/` 目录与文件名是**双重编码乱码**，标准文件 API 无法按中文名访问；需先按导
  出为 ASCII 文件名再读取（`cp` 到临时目录即可）。
- 本机**已有可用 PostgreSQL 18 + Redis**（配置在 `vctn-api/.env`，账号 `bmw730` **无 CREATEDB 权限**，无法建临时库）。
- 本机 pip / npm 网络很慢（pip 装 25 个包约 23 分钟），长任务务必后台跑。

## 路由装配约定（2026-10-01 修正，勿回退）
- **挂载前缀只写到模块基址**，业务段由 router 内部路径声明：
  `admin/*` → `/admin`（`admin/auth` 例外用 `/admin/auth`）；`platform/blog/tools/analytics/system` 各自
  router 内部已含模块段，故挂载前缀为 `""`、`/tools`、`/blog`、`/analytics`、`/files`、`/jobs`、`/search`。
- 判定标准：**OpenAPI 路径不得出现连续重复段**（`/users/users`）；多个 router 共用同一前缀是允许的。
- FastAPI 本版本 `app.routes` 无 `APIRoute`，枚举端点必须用 `app.openapi()["paths"]`。
- `router.__module__` 会回退成 `fastapi.routing`；要拿定义模块请用 `route.endpoint` / `inspect.getsource`。

## 权限口径（2026-10-01 确立）
- 权限码权威 = `aicoding/spec/07-API业务Spec/11-权限矩阵.md`（64 条）；控制器里 9 个矩阵外码
  已登记 `vctn-api/BLOCKERS.md`，属待决策差异。
- 端点级 API 权限由「实际路由 + 控制器真实 `require_permission` 依赖」生成，不维护手写映射表。

## 成长体系的管理端（2026-10-05 全部打通，B-33 已关闭，勿回退到说明页）
- 平台侧 `/growth/me`、`/points/me`、`/tasks/me` 等**仍是 `/me` 形式**，Operator 调用照样
  401 `401001`。**管理员一律走 `/api/v1/admin/...`**，不要再调任何 `/me` 端点。
- 管理员侧端点在 `vctn-api/app/admin/growth/`（router 挂 `("/admin", "admin:growth", ...)`）：
  `/admin/growth/overview`、`/admin/biz-users`、成长规则与积分规则 CRUD、`/admin/levels` CRUD、
  `/admin/tasks` CRUD，以及 `/admin/users/{id}/` 下的 summary / growth / growth.transactions /
  `POST growth.adjust` / points / points.transactions / `POST points.adjust` / levels /
  levels.history / tasks / achievements / cosmetics / cosmetics.equipment。
- **写操作必须委托** `GrowthService.apply_event` / `PointService.adjust`，禁止自己写账
  （否则丢幂等、行锁、version、等级重算、审计）。调整事件码 `ADMIN_ADJUST` 故意不播种规则。
- **等级与任务只能软删**（外键 `current_level_id` / `task_id` 会拦物理删），删前引用计数
  → 有引用返回 409001。不要再设计 `force=true`。
- `biz_user_growth_account` / `biz_user_point_account` **主键是 `user_id` 不是 `id`**，
  通用计数要传 `column` 覆盖。
- 矩阵外权限码 4 个（已登记 `seed/catalog.py::RUNTIME_EXTRA_PERMISSIONS`）：
  `BIZ_USER_VIEW`、`TASK_CONFIG_VIEW`、`TASK_CONFIG_EDIT`、`ACHIEVEMENT_CONFIG_VIEW`。
- 前端：`src/api/growth.ts` + `src/components/growth/BizUserPicker.vue` + `src/types/growth.ts`；
  六页（growth/points/levels/tasks/achievements/cosmetics）全部消费管理端接口。
  `BizIdentityNotice.vue` 已删除，不要再引用。
- 装扮页只读（没做「发放装扮」端点），别误以为坏了。

## Seed 初始数据（2026-10-01 落地）
- 代码：`vctn-api/app/scripts/seed/`；命令：`python -m app.scripts.seed [--mode=system|test] [--runs=N]`。
- 管理员初始密码只从 `VCTN_SEED_ADMIN_PASSWORD` 读（缺失即失败）；测试账号密码走 `VCTN_SEED_TEST_PASSWORD`。
- 幂等：只按稳定业务键 insert-if-not-exists，绝不 UPDATE 已有行；一次 run 一个事务。
- 文档：`SEED_DATA_DESIGN.md` / `SEED_DATA_REPORT.md` / `BLOCKERS.md`（均在 `vctn-api/`）。
