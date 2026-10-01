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

## 环境坑
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

## Seed 初始数据（2026-10-01 落地）
- 代码：`vctn-api/app/scripts/seed/`；命令：`python -m app.scripts.seed [--mode=system|test] [--runs=N]`。
- 管理员初始密码只从 `VCTN_SEED_ADMIN_PASSWORD` 读（缺失即失败）；测试账号密码走 `VCTN_SEED_TEST_PASSWORD`。
- 幂等：只按稳定业务键 insert-if-not-exists，绝不 UPDATE 已有行；一次 run 一个事务。
- 文档：`SEED_DATA_DESIGN.md` / `SEED_DATA_REPORT.md` / `BLOCKERS.md`（均在 `vctn-api/`）。
