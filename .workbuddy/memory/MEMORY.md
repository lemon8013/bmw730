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

## 已冻结 vs 待冻结（节选）
- 已冻结：ToolRegistry、ToolRuntime、component_key、FRONTEND/BACKEND/ASYNC、sys_user 与 biz_user 分离。
- 未冻结（遇到必须停下报 BLOCKER，禁止自行发明）：MFA Provider、Access/Refresh Token TTL、Redis key/TTL、权限缓存版本方案、Role Inheritance SQL、CUSTOM Data Scope 存储、日志分区、**UI 组件库**、最终 Tool API DTO、Error Code 完整目录（DD-12）、Pagination 语义（DD-13）、Snowflake 位布局（DD-14）、积分/等级/任务具体数值。

## 工程状态
- Phase 0 已完成并停止（2026-09-30）。提交：`b4ab41c`（工程骨架）、`38b746b`（验证报告）。
- 报告：`PHASE-0-VERIFICATION-REPORT.md`。
- 后端 venv：`vctn-api/.venv`（Python 3.13.14）；依赖锁：`vctn-api/requirements.lock.txt`。
- 待关闭：PG/Redis 连接信息（BLOCKER-1）；Spec 回写根目录与版本清单（BLOCKER-2）。

## 环境坑
- `aicoding/spec/` 目录与文件名是**双重编码乱码**，标准文件 API 无法按中文名访问；需先按索引导出为 ASCII 文件名再读取。
- 本机没有 PostgreSQL / Redis / Docker。
- 本机 pip / npm 网络很慢（pip 装 25 个包约 23 分钟），长任务务必后台跑。
