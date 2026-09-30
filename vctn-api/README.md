# vctn-api

VCTN 的统一 FastAPI 模块化单体后端。

## 说明

- 只有一个后端应用：所有业务模块挂载在同一个 FastAPI 实例上。
- 业务接口统一前缀 `/api/v1`。
- 系统探针位于根路径：`/health`、`/ready`、`/version`。
- 模块之间禁止通过 HTTP 互相调用。
- 数据库结构以冻结的 PostgreSQL DDL 为唯一来源
  （`aicoding/sql/vctn-enterprise-ddl-v2.0.sql`，79 张表）。
- 系统不支持多租户：禁止出现 `tenant_id` 等字段。
- 主键为 BIGINT，由应用层生成（Snowflake），数据库不参与自增。

## Phase 0 范围

本阶段只包含工程骨架与基础设施：配置系统、日志、Trace ID 中间件、统一响应封装、
异常体系、数据库/Redis 访问基础设施、健康检查与文档。

不包含任何业务功能（用户、部门、角色、权限、登录、Session、MFA、Tools、Blog、
积分、等级、Analytics、Audit）。

## Phase 1 范围：Model 与迁移

只做「Model + Migration + PostgreSQL」，不含业务 API 与业务逻辑。

- 79 个 Model 按业务域分布在 `app/<域>/<模块>/model.py`，全部继承同一个
  `app.shared.database.base.Base`。
- `app/shared/database/models.py` 是统一注册表，Alembic 以 `Base.metadata` 作为
  `target_metadata`，导入它即保证不漏表。
- 迁移 `0001_initial_schema` 由 Alembic 自动生成，全部使用 `op.create_table` /
  `op.create_index` 等 API，不含整段裸 DDL。
- 每张表、每个字段都带中文描述，落到 PostgreSQL 的 `COMMENT ON`。

### 约定（改动前请先读）

1. **不要再加自增**：单列 BIGINT 主键必须保留 `autoincrement=False`，否则
   SQLAlchemy 会生成 `BIGSERIAL` 与序列，与 Snowflake ID 冲突。
2. **不要恢复 `MetaData` 命名约定**：`base.py` 刻意不设 `naming_convention`，
   让 PostgreSQL 生成与冻结 DDL 一致的约束名（`*_pkey` / `*_fkey` / `*_key` /
   `*_check`）。唯一约束、CHECK 与 `tool.current_version_id` 外键已在 Model 中
   显式命名。
3. **`metadata` 列**：DDL 有 8 张表使用该列名，而 SQLAlchemy 保留了 `metadata`
   属性，因此 Python 侧属性名为 `metadata_payload`，数据库列名仍为 `metadata`。
4. **`tool` ↔ `tool_version` 是循环外键**：Model 侧用 `use_alter=True`；迁移中该
   外键必须单独 `op.create_foreign_key`，放在 `tool_version` 建表之后。

### 一致性校验

`scripts/schema_audit.py` 会在事务内执行冻结 DDL 并回滚，把 PostgreSQL 真实建出
的结构与 Alembic 迁移后的库逐项比对。

```bash
python scripts/schema_audit.py     # DDL == Model == PostgreSQL ?
alembic check                      # 检测 Model 与库之间的漂移
```

## 本地运行

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -e ".[dev]"

cp .env.example .env            # 填入 DB_HOST/DB_PORT/... 与 REDIS_HOST/...
alembic upgrade head            # 建表（首次）
uvicorn app.main:app --reload --port 8000
```

## 质量检查

```bash
ruff check .
ruff format --check .
mypy
pytest
```

## 数据库迁移

```bash
alembic current
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "message"
```
