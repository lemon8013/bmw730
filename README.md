# bmw730 — VCTN 项目工作区

VCTN 采用【双前端 + 单 FastAPI 模块化单体】架构。

```text
F:\project\bmw730\
├── vctn-api          FastAPI 模块化单体（唯一后端）
├── vctn-admin-web    管理平台前端
├── vctn-tools-web    Tools 平台前端
├── vctn-blog-web     博客前端
├── vctn-ops-web      运维监控前端
├── deploy            Nginx 模板与部署变量样例
├── scripts           备份、恢复、CentOS 引导脚本
├── docs              RUNBOOK、CentOS 部署手册
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

后端、四个前端与运维监控（ops）已实现；详细进度见 `docs/` 与 `GO-LIVE-CHECKLIST.md`。

## 文件与对象存储

所有上传的文件、图片与导出产物统一走 `vctn-api/app/shared/storage/`，两个后端：

| `FILE_STORAGE_PROVIDER` | 用途 | 说明 |
| --- | --- | --- |
| `s3` / `rustfs` | **生产** | 任意 S3 兼容端点，仓库默认跑 RustFS（也可换 MinIO / Ceph RGW / 云 OSS）。多副本看到同一份数据 |
| `local` | 单机试点 | 落在 `FILE_STORAGE_ROOT`；两个副本就是两份互不相干的数据，容器重启即丢 |

`rustfs` 只是 `s3` 的自解释别名，历史值 `minio` 继续可用，记录在库里的统一是 `s3`。

零新增依赖：用 `httpx` 加自研 AWS SigV4 直连 S3 API（依赖索引不允许另一个 S3 SDK），
并已用 AWS 官方文档的示例向量做过签名比对。切换只需改配置，业务代码不感知。

凭据填在 `.env` / `deploy/.env.deploy.example` 的 `S3_*` 段（旧的 `MINIO_*` 名仍可读取）；
填完跑 `python -m app.scripts.storage_check` 自检（写、读、删一个探针对象），
容器里是 `docker compose run --rm api check-storage`。

## 部署

- **CentOS / Rocky / AlmaLinux**：`docs/DEPLOY-CENTOS.md`（含容器与裸机两条路线，建议照序执行）
- 容器编排：`docker-compose.yml`（全栈）与 `docker-compose.managed.yml`（接托管数据库）
- 部署变量清单：`deploy/.env.deploy.example`，复制为仓库根目录 `.env` 后填写
- 值班与回滚：`docs/RUNBOOK.md`

> 四个前端都通过相对路径 `/api/v1` 调用后端，**没有反向代理转发 `/api/` 就是全白屏**，
> 且报错表现像 CORS 问题，容易误判。
