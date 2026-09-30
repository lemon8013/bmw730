# vctn-api

VCTN 的统一 FastAPI 模块化单体后端。

## 说明

- 只有一个后端应用：所有业务模块挂载在同一个 FastAPI 实例上。
- 业务接口统一前缀 `/api/v1`。
- 系统探针位于根路径：`/health`、`/ready`、`/version`。
- 模块之间禁止通过 HTTP 互相调用。
- 数据库结构以冻结的 PostgreSQL DDL 为唯一来源（Phase 0 不建表、不写业务 Model）。

## Phase 0 范围

本阶段只包含工程骨架与基础设施：配置系统、日志、Trace ID 中间件、统一响应封装、
异常体系、数据库/Redis 访问基础设施、健康检查与文档。

不包含任何业务功能（用户、部门、角色、权限、登录、Session、MFA、Tools、Blog、
积分、等级、Analytics、Audit）。

## 本地运行

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -e ".[dev]"

cp .env.example .env            # 填入 DATABASE_URL / REDIS_URL
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
alembic history
alembic revision --autogenerate -m "message"   # 由数据库阶段执行
```
