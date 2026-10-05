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
| **B-33** | **成长 / 积分 / 任务 / 装扮没有管理员侧读端点** | 现有全部端点均为 `/me` 形式，按**平台业务用户**取数；Operator 会话调用于是返回 401 `401001 a business user identity is required`。未自行发明 `/api/v1/admin/users/{user_id}/growth` 一类端点（新增 API 面 = 规格决策）。前端暂以说明组件替代报错区块，详见下方 §七 |
| **B-34** | ~~工具用量统计没有管理员可读的数据源~~ **已关闭（2026-10-05）** | 已新增 `GET /admin/tools/usage`（每工具使用次数）与 `GET /admin/tools/usage/daily`（按日序列），权限复用矩阵内已有的 `TOOL_STAT_VIEW`，均直接聚合 `tool_usage_event`，不依赖汇总表；`ToolStatisticsPage.vue` 已改为只消费管理端接口 + 公开热门榜，Operator 打开不再 401。详见下方 §八 |
| **B-35** | **工具访问策略粒度不足以支撑「指定用户 / 角色可见」** | `tool_access_policy` 唯一约束为 `(tool_id, subject_type)`，**无 `subject_id` 列**，且 `subject_type` 后端限定 `^(GUEST\|USER)$`（`app/tools/access/service.py`）。因此可见性只能分「游客 / 登录用户」两档，无法针对具体用户或角色。这是冻结 DDL 的结构限制，属规格决策，未改表。当前可用的两档控制见下方 §八 |
| **B-36** | **热门榜汇总表从未生成，tools-web 热门榜恒为空** | `tool_popularity_daily` 当前 0 行，`popular()` 读它，故 `/tools/popular` 返回 `[]`。唯一生成入口 `POST /tools/statistics/refresh` 与 `/tools/usage/refresh-popularity` 同样要求业务用户身份。**没有定时任务或触发器负责刷新**，也没有定义刷新频率与责任人，属未决的产品口径 |
| **B-37** | **行为分析全链路没有任何数据，`/analytics` 八个页签恒为空** | 实测行数：`behavior_event` / `behavior_event_daily` / `behavior_user_daily` / `behavior_page_daily` / `behavior_tool_daily` / `behavior_search_daily` / `behavior_funnel` **全部 0 行**；`POST /admin/analytics/recompute` 返回 `recomputed_rows: 0`。根因是**没有任何埋点上报方**：tools-web 调 `/tools/runtime/execute` 只写 `tool_usage_event`，admin-web 也不上报页面事件，规格未定义谁负责埋点。工具侧数据走的是另一条链路（`tool_usage_event` 31 行），因此「工具统计」有数而「行为分析」为空。属埋点范围与责任人的产品口径空缺，未自行发明埋点 |

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

---

## 七、本轮登记（2026-10-03 前端缺陷修复轮）：成长体系没有管理员侧读端点

### 现象

管理平台以 **Operator（`sys_user`）** 身份登录。成长体系的全部读端点都只有 `/me` 形式：

| 端点 | 身份来源 | Operator 会话结果 |
| --- | --- | --- |
| `/api/v1/growth/me`（及 `/me/transactions`） | 业务用户 | 401 `401001` |
| `/api/v1/points/me`（及 `/me/transactions`） | 业务用户 | 401 `401001` |
| `/api/v1/tasks`、`/api/v1/tasks/me` | 业务用户 | 401 `401001` |
| `/api/v1/levels/me`、`/api/v1/achievements/me`、`/api/v1/cosmetics/me` | 业务用户 | 401 `401001` |

OpenAPI 全部 162 条路径中，**不存在**任何 `/admin/growth`、`/admin/points`、`/admin/tasks`
形式的按用户查询端点。

而同一批资源里的**目录型**端点不鉴业务身份，Operator 可读：`/levels`、`/achievements`、
`/cosmetics`、`/point-rules/public`。这也是本次前端到现在仍能出数据的部分。

### 本轮处理（前端侧，未改动后端 API 面）

* `growth` / `tasks` 两页：整页依赖全是 `/me` 系列，改为渲染 **`BizIdentityNotice`**
  说明组件 + 指向可用目录页的入口，不再抛加载失败。
* `points` 页：保留可读的**积分规则**表格，账户与流水两块改为同一说明组件。
* `levels` / `achievements` / `cosmetics` 三页：**目录部分照常出数据**，仅「我的等级 /
  我的成就 / 我的装扮」三个区块改为说明组件。
* 删除已无调用方的 `api/growth.ts`、`api/tasks.ts`，并从 `points` / `levels` /
  `achievements` / `cosmetics` 四个 api 模块中移除对应的 `/me` 封装，避免留下会再次触发
  401 的死代码。

### 待决策（需先于后端实现）

1. 是否新增管理员侧查询端点？建议形态 `/api/v1/admin/users/{user_id}/growth`、
   `/points`、`/tasks`、`/levels`、`/achievements`、`/cosmetics`。
2. 若新增，其**权限码**需并入 §二-A 的矩阵差异清单（目前无对应冻结权限码）。
3. 若决定「管理平台不展示任何用户级成长数据」，则需在导航层面移除 `/growth*` 路由，
   而非保留说明页。

### 顺带修好的两处（非 BLOCKER）

* `/admin/roles?page_size=500` 返回 422：`MAX_PAGE_SIZE = 200`，而用户管理、角色管理两页
  的下拉选项请求写死 500。已抽出前端常量 `MAX_PAGE_SIZE`（与后端同名同值）并使用。
* `browser-verify.sh` 注入的占位 refresh token 只有 6 字符，低于后端 `min_length=8`，
  导致误报 422 并被误判成产品缺陷；占位值已加长。

---

## 八、工具可见性控制点与用量统计现状（B-34 / B-35 / B-36）

回答「如何在管理后台设置工具可见性」与「在哪里统计工具使用频率」两个问题时，
对当前实现做了完整勘查，结论如下。

### 1. 可见性：只有两档开关，粒度到「游客 / 登录用户」为止

判定顺序实现在 `app/tools/access/service.py::ToolAccessService.resolve()`：

| 步骤 | 判定 | 说明 |
| --- | --- | --- |
| 1 | `tool.status != ACTIVE` | 抛 `NotFoundError`，所有人都用不了 |
| 2 | `is_guest ? GUEST 策略 : USER 策略` | `subject_type` 只有这两个值 |
| 3 | 策略行不存在时回落配置 `TOOL_DEFAULT_VISIBILITY` | 现默认 `PUBLIC`（`Settings` + `.env.example` 同步）；改为 `REGISTERED` 则「游客默认禁止、登录用户默认允许」 |
| 4 | `enabled == False` | 抛 `BusinessRuleError`（400001），该身份不可用 |
| 5 | 配额校验 | 策略有值用策略值，否则回落 `TOOL_GUEST_DAILY_QUOTA` / `TOOL_USER_DAILY_QUOTA` |

对应的后台控制点：

* **对所有人生效**：`工具列表页 /tools` 的上线 / 下线
  （`PUT /admin/tools/{id}/status`，字典 `TOOL_STATUS` = `ACTIVE / DRAFT / OFFLINE / DEPRECATED`）。
  目录查询层 `active_tools()` 与 `tools_of_category()` 均过滤 `status == ACTIVE`，下线即刻从
  tools-web 消失。
* **按身份生效（推荐入口，2026-10-05 新增）**：`工具列表页 /tools` 的「可见性」列
  —— 行内下拉直接切换「所有人可用 / 注册用户可用」，走
  `PUT /admin/tools/visibility/{tool_id}`（权限 `TOOL_ACCESS_MANAGE`），内部 upsert
  GUEST + USER 两行策略并写审计与操作日志。列表读取走 `GET /admin/tools/visibility`。
* **细粒度配额**：`访问策略页 /tools/access-policies`
  （`PUT /admin/tools/access-policies/{tool_id}`，可设启用开关 + 每日上限 + 每分钟限流 + 并发上限）。

**读侧与执行侧已同步过滤（2026-10-05）**：此前只有 `resolve()` 检查 `enabled`，而执行路径
只调 `enforce_quota()`，**导致「注册用户可用」的工具游客仍可执行**，且目录接口完全不按策略过滤。
现已修：`ToolAccessService.enforce_quota()` 开头先做可见性拦截；目录的
`list_tools()` / `search()` / `get_by_slug()` / `get_tool()` / `popular()` 全部按调用者身份
（`OptionalPrincipal` 为空即游客）过滤，游客对隐藏工具一律 404（列表里不出现、按 slug 查不到）。
实测：切到 REGISTERED → 匿名列表 / 搜索 / slug 查询均 0 命中且 `by-slug` 返回 404、匿名执行返回
400001；切回 PUBLIC 后恢复。

**不能做的事**：指定「某个用户」或「某个角色」可见。原因见 B-35 —— 表里没有 `subject_id`，
`subject_type` 也被后端正则锁死为两种。要支持就必须动冻结 DDL 并引入新的 API 面与权限码，
属规格决策。

**已知副作用（已缓解）**：管理后台 `POST /admin/tools` 新建工具时**不会自动创建任何策略行**
（`app/admin/tools/service.py::create_tool` 未涉及 `ToolAccessPolicy`）。此前按步骤 3 的旧默认值
（`not is_guest`）意味着新建工具对游客不可用，与 tools-web 的匿名门户现状冲突；因此把默认值
外置为配置 `TOOL_DEFAULT_VISIBILITY`，默认 `PUBLIC`，新建工具与既有工具行为一致（对所有人开放），
需要时才由管理员改为 `REGISTERED`。未配置该键或取值非法时按 fail-closed 处理
（见 `default_subject_enabled()`）。

### 2. 用量统计：已落地管理员侧读取面（B-34 关闭）

2026-10-05 补齐了管理员可读的统计接口，统计页不再触碰业务用户端点：

| 新增端点 | 权限 | 说明 |
| --- | --- | --- |
| `GET /admin/tools/usage?days=30` | `TOOL_STAT_VIEW` | 每个工具的使用次数：总调用 / 成功 / 失败 / 独立用户 / 独立访客 / 最近使用，按调用次数降序 |
| `GET /admin/tools/usage/daily?tool_id=&days=30` | `TOOL_STAT_VIEW` | 单个工具的按日序列，用于趋势图 |
| `GET /admin/tools/visibility` | `TOOL_VIEW` | 每个工具的可见性（PUBLIC / REGISTERED） |
| `PUT /admin/tools/visibility/{tool_id}` | `TOOL_ACCESS_MANAGE` | 设置可见性，内部 upsert GUEST + USER 两行策略 |

统计口径直接聚合 `tool_usage_event`（原始明细），**不依赖 `tool_usage_daily` 汇总**，
因此即使从未刷新过汇总也能给出正确数字；前端 `ToolStatisticsPage.vue` 已改为只消费这三个
管理端接口 + 公开热门榜，Operator 打开不再 401。

### 3. 用量统计历史勘查（原始记录）

| 落库 | 内容 | 当前行数（2026-10-04） |
| --- | --- | --- |
| `tool_usage_event` | 每次执行一条明细，实时写入 | 29 |
| `tool_usage_daily` | 工具 × 日期汇总，与事件同事务写入 | 18 |
| `tool_popularity_daily` | 热门榜榜单，**无自动生成路径** | 0 |

管理后台 `/tools/statistics` 的三个数据源 `getUsageSummary` / `getUsageDaily` /
`getRecentUsage` 全部打到 `/tools/usage/*`，而该系列要求业务用户身份，Operator 必然 401。
实测打开该页会直接进入登录页，**且刷新令牌接续失败**（console 里两条 401：
`/tools/usage/recent?limit=20` 与 `/admin/auth/refresh`）。

热门榜因此恒为空：`/api/v1/tools/popular` 返回 `data: []`；而它唯一的生成入口
`POST /tools/statistics/refresh` 同样要求业务用户身份，且**没有任何定时任务负责调用**。

### 待决策（B-34 已关闭，剩余 B-35 / B-36）

1. ~~是否新增管理员侧用量读取面~~ —— **已关闭**：见上方「已落地管理员侧读取面」，
   权限复用矩阵内已有的 `TOOL_STAT_VIEW`，未新增权限码。
2. 热门榜刷新由谁触发、多久一次？目前既无定时任务也无责任人，属于产品口径空缺（B-36）。
   注：管理后台「刷新统计」按钮走 `POST /tools/statistics/refresh`（Admin 权限，可用），
   但只能手动触发。
3. 是否需要真正的「指定用户 / 角色」可见性？若需要，须先解冻 DDL 并新增
   `subject_id` 相关设计（B-35）。当前只支持「所有人可用 / 注册用户可用」两档。

