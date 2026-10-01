# VCTN 后端 — BLOCKERS / 未冻结项登记

本文件登记**所有「规格未冻结」与「实现和冻结契约存在差异」的条目**。按规则，遇到未冻结项
必须停下并登记，**不得自行发明**；差异同样如实登记，不静默绕过。

最后更新：Seed 实施轮次（`--mode=system` 三连跑 + `--mode=test` 双跑 + 数据库级校验全部完成）。

---

## 一、Seed 相关的未冻结项（本轮新登记）

| 编号 | 条目 | 状态 | 本轮处理方式 |
| --- | --- | --- | --- |
| **B-1** | 控制器使用了 **9 个不在冻结权限矩阵内**的权限码 | 已发现 | 照实 seed（否则运行期授权会落到不存在的码上），并在 §二-A 逐条列出 |
| **B-2** | **角色继承 SQL 规则未冻结** | 未冻结 | `sys_role_inheritance` **不写入任何行** |
| **B-3** | `DEPARTMENT_ADMIN` 的权限绑定未冻结 | 未冻结 | 角色建好，**授予 0 条权限** |
| **B-4** | `AUDITOR` 的权限矩阵未冻结 | 未冻结 | 角色建好，**授予 0 条权限** |
| **B-5** | **等级阈值（DD-16）未冻结** | 未冻结 | 仅初始化 `LV1`（`min_growth_points = 0`），不臆造阈值 |
| **B-6** | 成长值数值未冻结 | 未冻结 | 5 条规则绑定真实事件码，`growth_points = 0`、`enabled = false` |
| **B-7** | 积分数值未冻结 | 未冻结 | 5 条规则绑定真实事件码，`points = 0`、`enabled = false` |
| **B-8** | 任务 / 成就奖励未冻结 | 未冻结 | 各 3 条，`reward = NULL`、`status = DISABLED` |
| **B-9** | Feature Flag 全集未在规格中枚举 | 未冻结 | 只 seed 4 个「守卫已有子系统」的开关 |
| **B-10** | `CUSTOM` 数据范围存储方案未冻结 | 未冻结 | 只 seed `SCOPE_CUSTOM` 权限资源，不建映射数据 |
| **B-11** | **MFA Provider 未冻结** | 未冻结 | `MFA_ENABLED = false`，不初始化任何 provider |
| **B-12** | 分析原始埋点保留期未冻结 | 未冻结 | 配置项 `analytics.raw_event_retention_days` 值为 `NULL` 并带说明 |
| **B-13** | 工具访问策略的具体配额未冻结 | 未冻结 | `daily_limit` / `rate_limit_per_minute` / `concurrency_limit` 全部留空，`enabled = true` |
| **B-14** | 「系统配置表」应镜像哪些配置未在规格中枚举 | 未冻结 | 只镜像 `Settings` 中**已有代码默认值**的 38 项，数值不臆造 |

---

## 二、实现与冻结契约的差异（本轮登记）

### A. 权限码：控制器使用了 9 个矩阵外编码

冻结权限矩阵（`07-API业务Spec/11-权限矩阵.md`，64 条）是权限码的唯一权威。以下 9 个编码被
控制器 `require_permission("…")` 实际使用，但**不在**矩阵内：

| 矩阵外权限码 | 使用位置（示例） |
| --- | --- |
| `BLOG_CATEGORY_MANAGE` | `app/blog/categories/router.py` |
| `BLOG_COMMENT_REVIEW` | `app/blog/comments/router.py` |
| `EXPORT_MANAGE` | `app/admin/export/router.py` |
| `LOG_VIEW` | `app/admin/logs/router.py` |
| `NOTIFICATION_MANAGE` | `app/admin/notifications/router.py` |
| `SYSTEM_FILE_MANAGE` | `app/system/files/router.py` |
| `SYSTEM_JOB_MANAGE` | `app/system/jobs/router.py` |
| `TOOL_ACCESS_MANAGE` | `app/admin/tools/router.py`、`app/tools/access/router.py` |
| `TOOL_MANAGE` | `app/admin/tools/router.py`、`app/tools/catalog/router.py` |

**处置**：已 seed（`catalog.RUNTIME_EXTRA_PERMISSIONS`）以保证权限表与运行代码自洽，
但**需要决策**：把矩阵补齐（矩阵为准），或把控制器改为使用矩阵内编码。在决策前，
这 9 条一律视为偏离冻结契约。

### B. 端点覆盖差异

对照 `07-API业务Spec/endpoint-inventory.json`（205 条冻结端点，按各文档 Base 解析为规范全路径），
与实际运行路由（200 条 `METHOD+path`）：

| 指标 | 数量 |
| --- | --- |
| 冻结端点总数 | 205 |
| 实际运行端点总数 | 200 |
| 双方一致 | 126 |
| **冻结但未实现** | **79** |
| **已实现但未入册** | **74** |

本轮对路径做了**机械性归一**：修正了挂载前缀与 router 内部路径双重叠加导致的重复段
（`/admin/users/users`、`/admin/departments/departments`、`/platform/auth/auth`、
`/blog/articles/articles`、`/analytics/events/events`、`/tools/catalog/tools` 等），
并补齐了此前**未挂载**的 `platform/tasks`、`platform/achievements` 路由。归一后
OpenAPI 中已无重复段（157 → 162 条路径）。

结构性差异（不做机械改名，需设计决策）仍存在，例如：

* `system` 模块端点实现为 `/api/v1/files`、`/api/v1/jobs`、`/api/v1/search`（曾为 `/api/v1/system/*`）；
* Console 侧使用 `/admin/logs*`、`/admin/export/tasks*` 聚合端点，冻结契约使用 `/admin/(audit|security|operation|access)/logs`、`/admin/exports`；
* 工具管理使用 `PUT /admin/tools/{id}/status`，冻结契约使用 `POST /admin/tools/{id}/publish|disable`；
* 博客作者侧使用 `/blog/authors*`，冻结契约使用 `/blog/author/*`；
* 分析模块使用 `/analytics/(events|users|pages|tools|searches)/daily`，冻结契约使用 `/admin/analytics/*`。

<details>
<summary><b>B-15 · 冻结但未实现的 79 个端点</b>（点击展开）</summary>

```
DELETE /api/v1/admin/cosmetics/{id}                  (COSMETIC_EDIT)
DELETE /api/v1/admin/levels/{id}                     (LEVEL_CONFIG_EDIT)
DELETE /api/v1/admin/tool-categories/{id}            (TOOL_CATEGORY_EDIT)
DELETE /api/v1/admin/tools/{id}                      (TOOL_EDIT)
DELETE /api/v1/blog/author/articles/{id}             (Auth(Author))
GET    /api/v1/admin/analytics/events                (ANALYTICS_EVENT_VIEW)
GET    /api/v1/admin/analytics/funnels               (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/pages                 (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/retention             (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/search                (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/tools                 (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/trends                (ANALYTICS_VIEW)
GET    /api/v1/admin/analytics/users                 (ANALYTICS_VIEW)
GET    /api/v1/admin/blog/articles                   (BLOG_ARTICLE_REVIEW)
GET    /api/v1/admin/blog/author-applications        (BLOG_AUTHOR_REVIEW)
GET    /api/v1/admin/blog/author-applications/{id}   (BLOG_AUTHOR_REVIEW)
GET    /api/v1/admin/cosmetics                       (COSMETIC_VIEW)
GET    /api/v1/admin/exports                         (EXPORT_VIEW)
GET    /api/v1/admin/exports/{id}                    (EXPORT_VIEW)
GET    /api/v1/admin/growth-rules                    (GROWTH_RULE_VIEW)
GET    /api/v1/admin/levels                          (LEVEL_CONFIG_VIEW)
GET    /api/v1/admin/notifications/{id}              (NOTIFICATION_VIEW)
GET    /api/v1/admin/point-rules                     (POINT_RULE_VIEW)
GET    /api/v1/admin/tool-categories                 (TOOL_CATEGORY_VIEW)
GET    /api/v1/admin/tool-components                 (TOOL_COMPONENT_VIEW)
GET    /api/v1/admin/tools/popular                   (TOOL_STAT_VIEW)
GET    /api/v1/admin/tools/statistics/overview       (TOOL_STAT_VIEW)
GET    /api/v1/admin/tools/{id}/statistics           (TOOL_STAT_VIEW)
GET    /api/v1/admin/tools/{id}/versions             (TOOL_VERSION_VIEW)
GET    /api/v1/blog/author/application               (Auth)
GET    /api/v1/blog/author/articles                  (Auth)
GET    /api/v1/blog/author/articles/{id}             (Auth(Author))
GET    /api/v1/blog/author/me                        (Auth)
GET    /api/v1/blog/users/{id}                       (Public)
GET    /api/v1/files/{id}/download                   (Auth/Public按策略)
GET    /api/v1/tools/{id}/access                     (Public/Auth)
GET    /api/v1/users/me/achievements                 (Auth)
GET    /api/v1/users/me/cosmetics                    (Auth)
GET    /api/v1/users/me/growth                       (Auth)
GET    /api/v1/users/me/level                        (Auth)
GET    /api/v1/users/me/points                       (Auth)
GET    /api/v1/users/me/tasks                        (Auth)
GET    /health                                       (Public)
GET    /ready                                        (Public)
GET    /version                                      (Public)
POST   /api/v1/admin/analytics/export                (ANALYTICS_EXPORT)
POST   /api/v1/admin/blog/articles/{id}/approve      (BLOG_ARTICLE_REVIEW)
POST   /api/v1/admin/blog/articles/{id}/publish      (BLOG_ARTICLE_PUBLISH)
POST   /api/v1/admin/blog/articles/{id}/reject       (BLOG_ARTICLE_REVIEW)
POST   /api/v1/admin/blog/author-applications/{id}/approve (BLOG_AUTHOR_REVIEW)
POST   /api/v1/admin/blog/author-applications/{id}/reject  (BLOG_AUTHOR_REVIEW)
POST   /api/v1/admin/cosmetics                       (COSMETIC_EDIT)
POST   /api/v1/admin/exports/{id}/cancel             (EXPORT_CANCEL)
POST   /api/v1/admin/growth-rules                    (GROWTH_RULE_EDIT)
POST   /api/v1/admin/levels                          (LEVEL_CONFIG_EDIT)
POST   /api/v1/admin/point-rules                     (POINT_RULE_EDIT)
POST   /api/v1/admin/tool-categories                 (TOOL_CATEGORY_EDIT)
POST   /api/v1/admin/tool-components                 (TOOL_COMPONENT_EDIT)
POST   /api/v1/admin/tools/{id}/disable              (TOOL_PUBLISH)
POST   /api/v1/admin/tools/{id}/publish              (TOOL_PUBLISH)
POST   /api/v1/admin/tools/{id}/versions             (TOOL_VERSION_EDIT)
POST   /api/v1/admin/users/{id}/growth-adjustments   (USER_GROWTH_ADJUST)
POST   /api/v1/admin/users/{id}/point-adjustments    (USER_POINT_ADJUST)
POST   /api/v1/blog/author/applications              (Auth)
POST   /api/v1/blog/author/articles                  (Auth(Author))
POST   /api/v1/blog/author/articles/{id}/publish     (Auth(Author))
POST   /api/v1/blog/author/articles/{id}/submit-review (Auth(Author))
POST   /api/v1/files/complete                        (Auth/Public按业务策略)
POST   /api/v1/files/presign-upload                  (Auth/Public按业务策略)
POST   /api/v1/jobs/{id}/cancel                      (Auth)
POST   /api/v1/tools/jobs/{id}/cancel                (Auth)
POST   /api/v1/tools/{id}/usage                      (Public/Auth)
PUT    /api/v1/admin/cosmetics/{id}                  (COSMETIC_EDIT)
PUT    /api/v1/admin/growth-rules/{id}               (GROWTH_RULE_EDIT)
PUT    /api/v1/admin/levels/{id}                     (LEVEL_CONFIG_EDIT)
PUT    /api/v1/admin/point-rules/{id}                (POINT_RULE_EDIT)
PUT    /api/v1/admin/tool-categories/{id}            (TOOL_CATEGORY_EDIT)
PUT    /api/v1/admin/tools/{id}/access-policy        (TOOL_ACCESS_EDIT)
PUT    /api/v1/blog/author/articles/{id}             (Auth(Author))
```

注：`/health`、`/ready`、`/version` 实际已实现，只是在应用根路径（不含 `/api/v1`），
属比对口径差异而非缺失。

**这一组同时也解释了**为什么 27 个冻结矩阵权限码「无控制器引用」：它们对应的端点尚未实现。

</details>

<details>
<summary><b>B-16 · 已实现但未入册的 74 个端点</b>（点击展开）</summary>

```
DELETE /api/v1/analytics/funnels/{id}
DELETE /api/v1/blog/articles/{id}
DELETE /api/v1/blog/categories/{id}
GET    /api/v1/admin/analytics/events/daily
GET    /api/v1/admin/analytics/tool-usage
GET    /api/v1/admin/export/tasks
GET    /api/v1/admin/export/tasks/{id}
GET    /api/v1/admin/logs
GET    /api/v1/admin/logs/audit/traces/{id}
GET    /api/v1/admin/logs/{id}
GET    /api/v1/admin/notifications/stats
GET    /api/v1/admin/tools/access-policies
GET    /api/v1/analytics/events
GET    /api/v1/analytics/events/daily
GET    /api/v1/analytics/funnel-summary
GET    /api/v1/analytics/funnels
GET    /api/v1/analytics/identity-merges
GET    /api/v1/analytics/overview
GET    /api/v1/analytics/pages/daily
GET    /api/v1/analytics/searches/daily
GET    /api/v1/analytics/tool-rankings
GET    /api/v1/analytics/tools/daily
GET    /api/v1/analytics/trends
GET    /api/v1/analytics/users/daily
GET    /api/v1/blog/articles/review-queue
GET    /api/v1/blog/articles/{id}/tags
GET    /api/v1/blog/authors
GET    /api/v1/blog/authors/applications
GET    /api/v1/blog/authors/{id}
GET    /api/v1/blog/categories/{id}
GET    /api/v1/blog/comments/pending
GET    /api/v1/files
GET    /api/v1/jobs
GET    /api/v1/levels/me/history
GET    /api/v1/tools/access/policies
GET    /api/v1/tools/access/policy
GET    /api/v1/tools/jobs
GET    /api/v1/tools/statistics/popularity
GET    /api/v1/tools/statistics/usage-daily
GET    /api/v1/tools/usage/daily
GET    /api/v1/tools/usage/popularity
GET    /api/v1/tools/usage/recent
GET    /api/v1/tools/usage/summary
GET    /api/v1/users/me/equipment
POST   /api/v1/admin/analytics/recompute
POST   /api/v1/admin/export/tasks
POST   /api/v1/admin/export/tasks/{id}/retry
POST   /api/v1/admin/logs/{id}/export
POST   /api/v1/admin/notifications/{id}/read
POST   /api/v1/admin/users/batch-force-logout
POST   /api/v1/analytics/events
POST   /api/v1/analytics/funnels
POST   /api/v1/analytics/identity-merge
POST   /api/v1/analytics/recompute
POST   /api/v1/blog/articles
POST   /api/v1/blog/articles/{id}/publish
POST   /api/v1/blog/articles/{id}/review
POST   /api/v1/blog/authors/applications/{id}/review
POST   /api/v1/blog/authors/apply
POST   /api/v1/blog/categories
POST   /api/v1/blog/comments/{id}/review
POST   /api/v1/files
POST   /api/v1/jobs
POST   /api/v1/jobs/{id}/retry
POST   /api/v1/tools/jobs/{id}/retry
POST   /api/v1/tools/runtime/execute/{id}
POST   /api/v1/tools/statistics/refresh
POST   /api/v1/tools/usage/refresh-popularity
PUT    /api/v1/admin/tools/access-policies/{id}
PUT    /api/v1/admin/tools/{id}/status
PUT    /api/v1/analytics/funnels/{id}
PUT    /api/v1/blog/articles/{id}
PUT    /api/v1/blog/categories/{id}
PUT    /api/v1/tools/access/policies/{id}
```

**处置**：Seed 只登记**真实存在**的端点权限（不伪造未实现端点的权限）。
上表需要与冻结契约对齐后再决定：补齐规格、或从契约回写这些端点。

</details>

---

## 三、后端其余未冻结项（继承自 Backend 实施轮次）

| 编号 | 条目 | 现处理方式 |
| --- | --- | --- |
| **B-17** | MFA Provider 选型未冻结 | 不实现 provider，`MFA_ENABLED = false` |
| **B-18** | Access / Refresh Token 最终 TTL 未冻结 | 由 `Settings` 提供默认值并镜像到 `sys_config`，等待冻结后覆盖 |
| **B-19** | Redis key 命名与 TTL 规范未冻结 | 由 `Settings` 集中管理，未固化 key 模板文档 |
| **B-20** | 权限缓存版本方案未冻结 | 当前**不缓存**权限：每次请求经递归 CTE 查库（与规格要求一致） |
| **B-21** | 日志分区策略未冻结 | 保留期由 `Settings` 提供，未做分区 DDL |
| **B-22** | UI 组件库未冻结 | 前端选型待定，后端不受影响 |
| **B-23** | 最终 Tool API DTO 未冻结 | 采用当前内部 DTO，待冻结后对齐 |
| **B-24** | Error Code 完整目录（DD-12）未冻结 | 已有稳定错误码（如 `SEED_ADMIN_PASSWORD_REQUIRED`），完整目录待补 |
| **B-25** | Pagination 语义（DD-13）未冻结 | 沿用当前 `Page` / `PageParams` |
| **B-26** | Snowflake 位布局（DD-14）未冻结 | 由 `app.shared.ids` 配置化实现，位布局参数待冻结 |
| **B-27** | CUSTOM 数据范围的存储与解析未冻结 | 只保留权限资源与 `DataScope` 分支 |
| **B-28** | 「角色继承 SQL 规则」未冻结 | `AuthorizationService` 已有递归 CTE 实现，但**是否启用**待冻结 |

---

## 四、环境 / 工程级

| 编号 | 条目 | 现处理方式 |
| --- | --- | --- |
| **B-29** | Spec 中项目根目录写作 `D:\project\bmw730`，实际为 `F:\project\bmw730` | 以实际路径为准，待 Spec 回写 |
| **B-30** | `aicoding/spec/` 目录与文件名为双重编码乱码，标准文件 API 无法按中文名读取 | 读取前先导出为 ASCII 文件名 |
| **B-31** | 本机 PostgreSQL 账号 `bmw730` 无 `CREATEDB` 权限 | 无法用「全新空库」验证；改为在同一库上做增量 + 幂等验证，并用只读 SQL 独立校验 |
| **B-32** | Redis 未做端到端功能验证 | Seed 不依赖 Redis；Redis 相关链路待后续轮次验证 |

---

## 五、已解除

| 编号 | 条目 | 解除说明 |
| --- | --- | --- |
| ~~B-0-1~~ | 首次 seed 未写入端点级 API 权限（路由枚举得到 0 条） | 已定位为该 FastAPI 构建下 `app.routes` 不含 `APIRoute`，改用 `app.openapi()` 枚举；现覆盖 200/200 |
| ~~B-0-2~~ | 挂载前缀与 router 内部路径叠加导致重复段 | 已修正（157 → 162 条路径，重复段归零），并补齐未挂载的 tasks / achievements 路由 |
| ~~B-0-3~~ | 缺 `VCTN_SEED_ADMIN_PASSWORD` 时的失败路径 | 已验证返回 `SEED_ADMIN_PASSWORD_REQUIRED`，退出码 2 |
| ~~B-0-4~~ | **模型凭空多出一张表 `sys_export_task`**（冻结 DDL 中不存在） | 已删除该模型，导出模块改为复用冻结表 `sys_export_job`；详见下方 §六 |

---

## 六、本轮修复记录：`sys_export_task` 幽灵表

### 问题

`app/admin/export/model.py` 自行声明了一张 **冻结 DDL 中不存在**的表：

```
class SysExportTask(Base):
    __tablename__ = "sys_export_task"     # 违反：不得自行增删表
```

后果：

1. `Base.metadata` 变成 **80 张表**（DDL 为 79），列数 **772**（DDL 为 761），主键 79 → **80**；
2. `tests/integration/test_schema.py` 中 5 条模型/DDL 对齐测试全部失败；
3. 该表在数据库里**并不存在**，导出相关端点一旦真正落库就会以
   `relation "sys_export_task" does not exist` 失败。

### 修复

| 文件 | 变更 |
| --- | --- |
| `app/admin/export/model.py` | 删除 `SysExportTask`，改为 `from app.system.files.model import SysExportJob` 并 `ExportJob = SysExportJob` |
| `app/admin/export/repository.py` | 使用 `ExportJob`；`task_type` → `export_type` |
| `app/admin/export/service.py` | 审计/操作日志 `resource_type` 改为 `sys_export_job`；写入列对齐 DDL |
| `app/admin/export/schema.py` | DTO 字段对齐真实列：`task_type`→`export_type`、`params`→`filter_json`；移除无对应列的 `progress` / `updated_at`；补充 `row_count` / `started_at` |
| `app/admin/export/router.py` | 查询参数 `task_type` → `export_type` |
| `app/admin/logs/service.py` | 构造导出请求时改用 `export_type` / `filter_json` |
| `app/admin/logs/schema.py` | 删除未被任何地方引用的死代码 DTO `LogExportTriggerResponse` |
| `tests/unit/test_app_wiring.py` | 断言从「挂载前缀不得重复」改为「同一 METHOD+path 不得被两个 router 同时声明」+「OpenAPI 路径不得出现连续重复段」（更强、且与新装配一致） |

### 修复后校验

| 指标 | 修复前 | 修复后 | DDL 基线 |
| --- | --- | --- | --- |
| 模型表数 | 80 | **79** | 79 |
| 模型列数 | 772 | **761** | 761 |
| 主键数 | 80 | **79** | 79 |
| 外键数 | — | 82 | 82 |
| 模型 − DDL | `{sys_export_task}` | **∅** | — |
| 测试 | 7 failed / 88 passed | **136 passed** | — |

### 遗留（需决策，未自行发明）

* `ExportTaskResponse` 现在只暴露 `sys_export_job` 真实存在的列。原实现里的
  `progress`（进度百分比）在 DDL 中**没有对应列**，已从响应中移除——因为导出状态机已由
  `status` + `started_at` / `finished_at` 完整表达。若产品确实需要进度百分比，
  需先冻结该列的存储位置（新增列 = 改库，必须由规格决定）。
* 端点命名仍为 `/api/v1/admin/export/tasks*`，而冻结契约使用 `/api/v1/admin/exports`；
  归类为 §二-B 的路径差异，未在本轮改名。

