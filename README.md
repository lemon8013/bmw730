# bmw730 — VCTN 项目工作区

VCTN 采用【双前端 + 单 FastAPI 模块化单体】架构。

```text
F:\project\bmw730\
├── vctn-api          FastAPI 模块化单体（唯一后端）
├── vctn-admin-web    管理平台前端
├── vctn-tools-web    Tools 平台前端
└── aicoding          Spec / DDL 基线包（需求唯一来源）
```

```text
vctn-admin-web ─┐
                ├──►  vctn-api  ──►  PostgreSQL
vctn-tools-web ─┘                 └──►  Redis
```

## 工程规则

- 只有一个后端：`vctn-api`。禁止拆分微服务，禁止模块之间通过 HTTP 互相调用。
- 两个前端完全独立，不互相 import，共享的是后端 API Contract。
- 依赖不得自行增加或替换；未在 `aicoding/spec/08-EnterpriseBaseline/DEPENDENCY-INDEX.md` 清单中的包一律视为 BLOCKER。
- 数据库结构以 `aicoding/sql/vctn-enterprise-ddl-v2.0.sql` 为唯一来源。
- 系统不支持多租户：禁止增加 `tenant_id`。
- 系统 ID 为 BIGINT + Snowflake；API JSON 中 BIGINT ID 序列化为 string。
- 时间统一 UTC，API 使用 ISO 8601。

## Spec 位置

```text
aicoding/
├── VCTN-Complete-Spec-V2.2.md          完整总 Spec
├── spec/                               分类 Spec（总纲/后端/前端/Tools/API/Baseline）
└── sql/vctn-enterprise-ddl-v2.0.sql    PostgreSQL DDL 基线
```

> 注：`aicoding/README.md` 中冻结的项目根目录写作 `D:\project\bmw730`，
> 本工作区实际位于 `F:\project\bmw730`（由项目负责人在 Phase 0 确认）。
> 后续如需迁移，三份工程可整体平移到 D 盘对应路径，无需修改任何代码。

## 当前状态

Phase 0：工程骨架 + 基础设施 + 启动验证。尚未实现任何业务功能。
