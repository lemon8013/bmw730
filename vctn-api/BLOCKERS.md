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
| ~~B-33~~ | ~~成长 / 积分 / 任务 / 装扮没有管理员侧读端点~~ **已关闭（2026-10-05）** | 负责人授权「成长/积分/任务 你拥有所有权限」。已新增 `app/admin/growth/` 模块（24 个端点，挂载在 `/api/v1/admin`），覆盖总览、业务用户检索、成长规则/积分规则/等级/任务 CRUD、以及按用户的成长账户、流水、成长值调整、积分账户、流水、积分调整、等级与升级历史、任务进度、成就、装扮、装备、汇总。写操作复用 `GrowthService.apply_event` / `PointService.adjust`，不复制记账逻辑。详见下方 §七 |
| **B-34** | ~~工具用量统计没有管理员可读的数据源~~ **已关闭（2026-10-05）** | 已新增 `GET /admin/tools/usage`（每工具使用次数）与 `GET /admin/tools/usage/daily`（按日序列），权限复用矩阵内已有的 `TOOL_STAT_VIEW`，均直接聚合 `tool_usage_event`，不依赖汇总表；`ToolStatisticsPage.vue` 已改为只消费管理端接口 + 公开热门榜，Operator 打开不再 401。详见下方 §八 |
| **B-35** | **工具访问策略粒度不足以支撑「指定用户 / 角色可见」** | `tool_access_policy` 唯一约束为 `(tool_id, subject_type)`，**无 `subject_id` 列**，且 `subject_type` 后端限定 `^(GUEST\|USER)$`（`app/tools/access/service.py`）。因此可见性只能分「游客 / 登录用户」两档，无法针对具体用户或角色。这是冻结 DDL 的结构限制，属规格决策，未改表。当前可用的两档控制见下方 §八 |
| **B-36** | **热门榜汇总表从未生成（已部分解决 2026-10-05）** | `tool_popularity_daily` 仍为 0 行，没有任何定时任务刷新它，`tool_popularity_daily` 的生成入口（`POST /tools/statistics/refresh` 等）也要求业务用户身份。**已做的兜底**：`ToolCatalogService.popular()` 在汇总表为空时回退到直接聚合 `tool_usage_event`（新 `ToolUsageRepository.popularity_from_events`），所以 `/tools/popular` 与 tools-web 热门页现在有数据。**仍未决**：汇总表的刷新频率与责任人依旧空缺，回退只是绕过它，不是替代它 |
| **B-38** | **平台侧业务动作在冻结 DDL 里没有审计落点（2026-10-06 发现并降级处理）** | `sys_operation_log.operator_id` 与 `sys_audit_log.operator_id` 均为 `REFERENCES sys_user(id)`，而博客投稿 / 评论 / 点赞等动作的发起者是**平台业务用户**（`biz_user`），直接写入必然 `ForeignKeyViolationError`（`POST /blog/authors/apply` 曾稳定 500）。**已做的降级**：`write_operation_log` 与 `AuditService.record` 新增 `actor` 参数——operator 写 id 列，平台用户写 `operator_id = NULL` 并把 `subject_id` / `subject_type` 记入 `metadata` / `after_data`（21 处 blog 调用 + 全部 `actor=actor` 审计调用已切换）。**仍未决**：平台侧动作到底该进哪张表没有规格依据；`sys_security_log.user_id` 无外键但语义上是安全事件流，不适合承载业务操作审计。详见下方 §九 |
| **B-37** | **行为分析全链路没有任何数据，`/analytics` 八个页签恒为空** | 实测行数：`behavior_event` / `behavior_event_daily` / `behavior_user_daily` / `behavior_page_daily` / `behavior_tool_daily` / `behavior_search_daily` / `behavior_funnel` **全部 0 行**；`POST /admin/analytics/recompute` 返回 `recomputed_rows: 0`。根因是**没有任何埋点上报方**：tools-web 调 `/tools/runtime/execute` 只写 `tool_usage_event`，admin-web 也不上报页面事件，规格未定义谁负责埋点。工具侧数据走的是另一条链路（`tool_usage_event` 31 行），因此「工具统计」有数而「行为分析」为空。属埋点范围与责任人的产品口径空缺，未自行发明埋点 |

---

## 四、环境 / 工程级

| 编号 | 条目 | 现处理方式 |
| --- | --- | --- |
| **B-29** | Spec 中项目根目录写作 `D:\project\bmw730`，实际为 `F:\project\bmw730` | 以实际路径为准，待 Spec 回写 |
| **B-30** | `aicoding/spec/` 目录与文件名为双重编码乱码，标准文件 API 无法按中文名读取 | 读取前先导出为 ASCII 文件名 |
| **B-31** | 本机 PostgreSQL 账号 `bmw730` 无 `CREATEDB` 权限 | 无法用「全新空库」验证；改为在同一库上做增量 + 幂等验证，并用只读 SQL 独立校验 |
| **B-32** | Redis 未做端到端功能验证 | Seed 不依赖 Redis；Redis 相关链路待后续轮次验证 |
| **B-37**（已记录，非阻塞） | 对象存储需要 S3 客户端，但 `DEPENDENCY-INDEX.md` 后端 Runtime 只有 `httpx`，清单里没有 `boto3` / `minio` / `rustfs` SDK | **不新增依赖**：在 `app/shared/storage/signer.py` 用标准库（`hmac` / `hashlib`）自行实现 AWS SigV4，传输仍走 `httpx`。签名已通过 AWS 官方文档的示例向量（canonical hash 与 `X-Amz-Signature` 逐字一致）验证；若后续 Spec 允许引入 SDK，可直接替换后端实现而不动调用方 |
| **B-38**（已记录，非阻塞） | 部署目标为 RustFS（S3 兼容、Apache 2.0），`DEPENDENCY-INDEX.md` 没有对应客户端条目 | 与上一条同一结论：RustFS 只被当作一个 S3 HTTP 端点使用，配置面用通用 `S3_*`（`MINIO_*` 作为历史别名保留），不引入任何厂商 SDK |

------

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

## 七、成长体系的管理员侧端点（B-33：2026-10-03 登记 / 2026-10-05 关闭）

> **状态：已关闭。** 负责人于 2026-10-05 授权「成长/积分/任务 你拥有所有权限」，
> 管理员侧端点已实现并浏览器验证通过。本节先记**本轮解法**，随后保留 2026-10-03
> 的原始登记内容作为历史背景。

### 解法一：新增 `app/admin/growth/` 模块（24 个端点，挂载在 `/api/v1/admin`）

| 文件 | 职责 |
| --- | --- |
| `app/admin/growth/schema.py` | 全部管理员侧 DTO（账户、流水、调整入参/出参、规则、等级、任务、成就、装扮、装备、汇总、总览） |
| `app/admin/growth/repository.py` | `AdminGrowthRepository`：业务用户检索、任务/规则/等级 CRUD、成就与装扮矩阵、升级历史、计数器 |
| `app/admin/growth/service.py` | `AdminGrowthService`：读侧组装 + 写侧**委托**给既有平台 Service |
| `app/admin/growth/router.py` | 全部端点，逐条挂 `require_permission(...)` |
| `app/main.py` | `_BUSINESS_ROUTERS` 增加 `("/admin", "admin:growth", admin_growth_router)` |

端点清单（`/api/v1/admin` 前缀下）：

* 总览与检索：`GET /growth/overview`、`GET /biz-users`
* 成长规则：`GET/POST /growth/rules`、`PUT/DELETE /growth/rules/{rule_id}`
* 积分规则：`GET/POST /points/rules`、`PUT/DELETE /points/rules/{rule_id}`
* 等级：`GET/POST /levels`、`PUT/DELETE /levels/{level_id}`
* 任务：`GET/POST /tasks`、`PUT/DELETE /tasks/{task_id}`
* 按用户：`GET /users/{user_id}/summary`、`/growth`、`/growth/transactions`、
  `POST /growth/adjust`、`/points`、`/points/transactions`、`POST /points/adjust`、
  `/levels`、`/levels/history`、`/tasks`、`/achievements`、`/cosmetics`、`/cosmetics/equipment`

**关键设计：委托而非复制。** 管理员侧的「调整成长值 / 调整积分」不自己写账，而是调用
`GrowthService.apply_event` 与 `PointService.adjust`，因此幂等键、`SELECT ... FOR UPDATE`
行锁、`version` 自增、等级重算、审计日志全部照常生效。调整使用的事件码
`ADMIN_ADJUST` **故意不在规则表里播种**，保证「管理员填多少就是多少」，不会被规则倍率二次放大。

**删除一律软删。** `biz_user_growth_account.current_level_id` 与 `biz_user_task.task_id`
都是外键，物理删除会被 PostgreSQL 拒绝；等级/任务的删除接口因此只写 `deleted_at`
+ 状态置 `DISABLED`，并先做引用计数，有引用时返回 `409001`
（实测：`"2 user record(s) still reference this level"`）。

**主键差异。** `biz_user_growth_account` 与 `biz_user_point_account` 以 `user_id`
为主键而非 `id`；通用计数方法 `count_rows` / `count_rows_where` 因此接受 `column`
覆盖参数，调用处显式传 `BizUserGrowthAccount.user_id` / `BizUserPointAccount.user_id`。

### 解法二：权限码

冻结矩阵内已存在的码直接复用：`LEVEL_CONFIG_VIEW/EDIT`、`GROWTH_RULE_VIEW/EDIT`、
`POINT_RULE_VIEW/EDIT`、`COSMETIC_VIEW/EDIT`、`USER_GROWTH_ADJUST`、`USER_POINT_ADJUST`。

**矩阵外新增 4 个**（已登记进 `app/scripts/seed/catalog.py::RUNTIME_EXTRA_PERMISSIONS`，
即规格差异的既定登记处）：

| 权限码 | 用途 |
| --- | --- |
| `BIZ_USER_VIEW` | 管理员检索平台业务用户（用户选择器） |
| `TASK_CONFIG_VIEW` | 查看任务定义 |
| `TASK_CONFIG_EDIT` | 新建/编辑/停用任务定义 |
| `ACHIEVEMENT_CONFIG_VIEW` | 查看成就定义 |

重新 seed 后 `SUPER_ADMIN` 持 **407 / 407** 权限，4 个新码均已授予。

### 解法三：补齐被留空的默认配置（顺带发现的独立缺陷）

原 seed 里成长体系**全部数值均为惰性占位**：只有 1 个等级（LV1）、规则 `enabled=false`
且积分为 0、任务与成就状态 `DISABLED` 且无奖励。已改为播种真实默认值：

* 等级阶梯 5 级：LV1(0) / LV2(100) / LV3(300) / LV4(1000) / LV5(3000)
* 成长规则 5 条、积分规则 5 条，`enabled=true`，含真实积分值与每日上限
* 任务 3 条、成就 3 条，状态 `ACTIVE`，附积分 / 成长值奖励

因 seed 是 **insert-if-not-exists（绝不 UPDATE 已有行）**，另用一次性脚本把新默认值回填进
既有库（退役遗留的 `LV_2` 测试等级、补齐阶梯、启用规则、挂奖励、`GrowthService.recalculate()`
重算全部用户等级）。该脚本已随本轮结束删除。

### 顺带修好的既有 Bug：`PointService.ensure_account`

`app/platform/points/service.py::ensure_account` 原实现调用
`self._repository.ensure_account(...)`，而该方法是 `GrowthService` 才有、`GrowthRepository`
**根本没有**的——任何「积分账户首次创建」都会 `AttributeError` 500。之所以此前从未暴露，
是因为积分表一直是空的。已改为用 `account_for_update` + `create_account` 两个仓储原语实现，
并在创建积分账户前先确保成长账户存在（外键依赖）。

### 验证结果

| 项 | 结果 |
| --- | --- |
| `GET /admin/growth/overview` | `biz_user_count 1`、`growth_account_count 1`、`point_account_count 1`、`growth_rule_enabled 5/5`、`point_rule_enabled 5/5`、`level_count 5`、`task_count 3`、`achievement_count 3`、`cosmetic_count 6` |
| 等级自动重算 | +50 → LV1；再 +60 → **LV2 自动升级**，`level_changed: true` |
| 删除保护 | 删除有引用的等级 → `409001` |
| 页面验证 | `/growth`、`/growth/points`、`/growth/levels`、`/growth/tasks`、`/growth/achievements`、`/growth/cosmetics` 六页全部出数据，**控制台 0 错误** |
| 页内调整流程 | 选 `testuser` → 调整 `-10` → 累计成长值 100 / Lv.2 进阶 / 还需 200 / 33%，流水新增 `-10 / 100 / EARN / ADMIN_ADJUSTMENT` |
| 后端 | `ruff check app` 全过；`pytest -q` **137 passed** |
| 前端 | `vue-tsc --noEmit` 无输出；`eslint src` 无输出 |

---

### 原始登记（2026-10-03 现象记录）

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

### 当时的临时处理（2026-10-03，前端侧，未改动后端 API 面）

* `growth` / `tasks` 两页：整页依赖全是 `/me` 系列，改为渲染 **`BizIdentityNotice`**
  说明组件 + 指向可用目录页的入口，不再抛加载失败。
* `points` 页：保留可读的**积分规则**表格，账户与流水两块改为同一说明组件。
* `levels` / `achievements` / `cosmetics` 三页：**目录部分照常出数据**，仅「我的等级 /
  我的成就 / 我的装扮」三个区块改为说明组件。
* 删除已无调用方的 `api/growth.ts`、`api/tasks.ts`，并从 `points` / `levels` /
  `achievements` / `cosmetics` 四个 api 模块中移除对应的 `/me` 封装，避免留下会再次触发
  401 的死代码。

### 当时的待决策项（2026-10-05 逐条答复）

1. **是否新增管理员侧查询端点？** → **是**，已实现，见本节开头「解法一」。实际形态为
   `GET /api/v1/admin/users/{user_id}/growth` / `points` / `tasks` / `achievements` /
   `cosmetics`，与当初建议一致；额外补了 `summary`、`levels`、`levels/history`、
   `cosmetics/equipment` 与两个调整端点。
2. **权限码需并入矩阵差异清单** → 已并入
   `app/scripts/seed/catalog.py::RUNTIME_EXTRA_PERMISSIONS`（4 个新码，见「解法二」）。
3. **是否在导航层移除 `/growth*`** → **否**，六页已全部改为消费管理员侧端点出真实数据；
   占位说明组件 `BizIdentityNotice.vue` 已删除。

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


---

## 九、独立博客前端 `vctn-blog-web` 与随之暴露的后端缺陷（2026-10-06）

### 背景

博客是独立域名、独立前端工程 `vctn-blog-web`（端口 5175），后端仍是唯一的
`vctn-api`，**不新建 blog-api**。前台匿名可读，登录后才可点赞 / 收藏 / 评论 /
关注，申请成为作者后可投稿与发布。

### 本轮新增

* 工程 `vctn-blog-web/`：`types/{api,blog,auth}.ts`、`api/{client,credentials,
  session,auth,blog}.ts`、`stores/auth.ts`、`composables/use-async-data.ts`、
  `layouts/AppLayout.vue`、`components/{UserMenu,ArticleCard,FeedState}.vue`、
  `pages/{Home,Search,Category,Article,Authors,Author,Mine,Login}Page.vue`、
  `scripts/browser-verify.sh`。
* 后端新增 `GET /blog/articles` 的 `author_id` 过滤参数（作者主页需要）。

### 修掉的四个后端既有缺陷

| # | 现象 | 根因 | 处理 |
| --- | --- | --- | --- |
| 1 | `POST /blog/authors/apply` 稳定 500 | `sys_operation_log.operator_id REFERENCES sys_user(id)`，平台业务用户写入违反外键 | `write_operation_log` 新增 `actor` 参数，operator 写 id、平台用户写 `NULL` + `metadata`；blog 21 处调用改为传 `actor`。`AuditService.record` 同步处理（原本传 `actor=` 直接 `TypeError`）。规格缺口登记为 **B-38** |
| 2 | `GET /blog/authors/applications` 返回 500 `invalid literal for int(): 'applications'` | 路由注册顺序：`/authors/{author_id}` 在 `/authors/applications` 之前，字面量段被当 id 解析 | 把 `apply` / `applications` 全部移到 `{author_id}` 之前；新增契约测试 `tests/contract/test_blog_access_contract.py` 锁住顺序 |
| 3 | 文章列表 `total` 恒为「行数 × 行数」（5 篇报 25） | `select(func.count(BlogArticle.id)).select_from(base.subquery())` —— `func.count(实体列)` 让外层隐式 FROM 主表，与子查询交叉连接 | 改为 `select(func.count()).select_from(...)`，blog 四个模块共 7 处 |
| 4 | `GET /blog/articles?status=DRAFT` 匿名即可列出**所有作者**的草稿 | 列表端点用 `OptionalPrincipal`，`status` 直接透传且不过滤作者 | 非 `PUBLISHED` 状态强制要求平台身份，并把结果收敛到调用者自己的作者行；新增单元测试 `tests/unit/test_blog_article_list_scope.py`（4 例） |

### 已知行为（不是缺陷）

* 评论提交后为 `PENDING`，`GET /comments` 只返回 `APPROVED`，需管理员在
  `/blog/comments/pending` 审核通过后才可见。前端已提示「审核通过后可见」。
* 文章列表分页参数是 `page` / `page_size`，**不是** `limit`。

### 本次新增测试

* `tests/contract/test_blog_access_contract.py` —— 字面量路由必须先于参数化路由。
* `tests/unit/test_blog_article_list_scope.py` —— 草稿可见性规则（4 例）。
* 后端全量：`ruff check app tests` 通过，`pytest -q` **143 passed**。

---

# Ops 监控系统（2026-10-07 交付）

## 已解决的 OPS-DECISION-001 ~ 012

采用负责人确认的推荐决策包，详见根目录 `OPS-PHASE-0-REVIEW.md` 与
`OPS-VERIFICATION-REPORT.md`。要点：PostgreSQL 普通表 + 小时/天 rollup、Agent 走
HTTPS REST + token、实时用前端轮询、日志复用既有 PG 日志表、自研阈值+持续时长+指纹
告警引擎、采集 60s、保留 7/30/180 天、阈值全配置化、通知 V1 仅 Webhook（Provider
注册表扩展）、高风险操作双审计、SLO 不在 V1、容量基线 50 主机 / 2000 序列。

## Ops 剩余 Blocker（OPS-BLOCKER-01 ~ 04）

| 编号 | 内容 |
| --- | --- |
| OPS-BLOCKER-01 | Job 采集器未接入（`/ops/jobs` 只读聚合既有 `sys_job*` 表） |
| OPS-BLOCKER-02 | Agent 真实探针进程不在本次交付范围（只交付注册/心跳/上报协议） |
| OPS-BLOCKER-03 | 告警规则无默认阈值种子（Spec 只要求可配置，未给默认值） |
| OPS-BLOCKER-04 | `MENU_OPS_CONSOLE` 未授予 SUPER_ADMIN 以外的角色（按需授权） |

## Ops 关键实现事实（防回退）

* **`ops_host.agent_id` 无外键**（与 `ops_agent.host_id` 成环，Alembic 无法排序），
  由应用层维护一致性——不要"补"上 FK。
* **指标目录是入库闸门**：`MetricService.create_samples` 拒绝未定义的 metric_key；
  目录来自 `app/scripts/seed/catalog.py::OPS_METRIC_DEFINITIONS`（51 条），
  没播种就一条样本都进不来。
* **告警→通知派发唯一入口**是 `app/ops/notifications/dispatcher.py::NotificationDispatcher`，
  由评估器 `_fire` 接线；规则 `notification_policy` 支持 `channel_codes`（别名
  `channels`）与 `group_codes`（组展开）。**无策略 = 不通知 + 零数据库访问**（刻意设计）。
* **维护窗口抑制**入口是 `MaintenanceService.suppresses_notifications()` /
  `MaintenanceRepository.find_suppressing()`；命中窗口写 `SKIPPED` 的
  `ops_alert_notification`，绝不外发。再触发（RESOLVED→FIRING）才重新派发，
  FIRING/ACKNOWLEDGED 每轮都发会刷爆渠道。
* 管理员侧全部走 `/api/v1/ops/*`；22 个 `OPS_*` + 19 个菜单节点已播种并授予 SUPER_ADMIN。

## Ops 交付验证

* 后端 `pytest -q`：**244 passed, 0 xfail**；`ruff check app tests` 通过。
* 端到端链路（`vctn-api/.devtools/verify_ops_chain.py`）：14/14 通过，
  含 Webhook 实发（本地接收器收到 payload）与维护窗口抑制（SKIPPED 且零外发）。
* 前端 `vctn-ops-web`（5176）：真实浏览器遍历 18 页全部可达、0 控制台错误；
  `vue-tsc` / `eslint` / `vite build` 通过（暂无组件级单测）。
