# VCTN 运维监控系统 — Phase 0 需求审查报告

> 依据：`aicoding/spec/ops/`（V1.1，44 个文件）
> 阶段：Phase 0（需求审查）完成；**Phase 1（技术方案决策）未完成，阻塞 Phase 2 及以后**
> 项目根目录：`F:\project\bmw730`（Spec 原文写 `D:\project\bmw730`，沿用既有负责人决策）

---

## 1 审查结论

| 项 | 结论 |
|---|---|
| 业务需求 | 已冻结，可进入设计（19 项 V1 范围明确） |
| 技术架构 | 已确定：单 FastAPI 模块化单体 + PostgreSQL + Redis + Vue3/TS |
| 数据模型 | **候选表清单，字段未冻结**（25 章明确"不在本 Spec 中冻结最终字段"） |
| 实现方案 | **12 项全部未决策**（40 章），Phase 1 未完成 |
| 能否直接开工 | **不能完整开工**。可先行部分：工程脚手架、权限码、审计集成、非时序表设计 |

Spec 41 章「BLOCKER 行为」规定：遇到 `OPS-DECISION-*` 必须停止对应实现、输出 BLOCKER、列出待确认选项、**不允许猜测**。因此本报告先冻结决策项，等待确认后再进入 Phase 2。

---

## 2 BLOCKER 清单（OPS-DECISION-001 ~ 012）

每项给出：**影响范围** / **候选** / **推荐值（最小 V1，不引入新组件）** / **不决策的后果**。

| ID | 决策 | 影响 | 推荐值 | 不决策后果 |
|---|---|---|---|---|
| 001 | Metrics 存储 | `ops_metric_sample/hourly/daily` 表结构、分区、索引 | **现有 PostgreSQL 普通表**（无新组件，小规模 V1） | 指标表无法建，Metrics/告警评估/图表全停 |
| 002 | Agent 通信 | Agent 注册/心跳/指标上报接口形态 | **HTTPS REST**（复用现有 FastAPI + Agent Token） | Agent 采集通道无法定，只能做注册/心跳 |
| 003 | 实时推送 | 前端刷新技术 | **前端轮询 Polling**（无新组件、无长连接治理） | 页面定时刷新策略未定 |
| 004 | Logs 存储 | 日志查询数据源 | **复用现有 PG 日志表**（33 章明确"优先复用"） | 日志中心数据源未定 |
| 005 | Alert Engine | 告警评估方式 | **自研规则引擎**（阈值+duration+fingerprint 去重） | 告警只能人工录入，无法自动触发 |
| 006 | Metrics 采集周期 | 采集器调度间隔 | **60 秒** | 调度器无法配置 |
| 007 | Metrics 保留期 | 清理任务与分区 | **原始 7 天 / 小时聚合 30 天 / 天聚合 180 天** | 清理任务与容量不可定 |
| 008 | Alert 默认阈值 | 规则默认参数 | **CPU 85%/5min、内存 90%/5min、磁盘 85%/10min、错误率 5%/5min、P95 1s/5min**（全部可配置，不硬编码） | 默认规则无法播种 |
| 009 | Notification V1 渠道 | 通知 Provider 实现范围 | **仅 Webhook**（无需第三方凭据、可本地测试） | 通知只能落记录，不能真实发送 |
| 010 | 高风险操作模型 | Job Retry/Stop、Agent 停用等 | **权限码 + 二次确认 + 强制审计**（不引入独立审批流） | 高风险操作无统一模型 |
| 011 | SLO/SLA 目标 | 是否在 V1 落地 | **V1 不实现**（仅保留扩展位） | 无影响，延后 |
| 012 | 容量基线 | 主机数/指标数/并发 | **V1 基线：50 主机、2000 指标序列、60s 间隔** | 压测与容量验收无基准 |

> 推荐值统一遵循一条原则：**复用现有基础设施，不新增组件、不新建依赖**——与 Spec 01.3/03 章"继续使用模块化单体、复用现有 PG/Redis"一致，也符合 DEPENDENCY-INDEX 约束（不自行添加依赖）。

---

## 3 矛盾与缺口清单（Contradiction List）

| # | 矛盾 / 缺口 | 说明 | 建议 |
|---|---|---|---|
| C1 | 根目录不一致 | Spec 写 `D:\project\bmw730`，实际工程在 `F:\project\bmw730` | 沿用现有 `F:`，不迁移 |
| C2 | 服务监控默认清单过时 | 06 章列 admin/tools/ops + PG/Redis/Nginx，未含已建成的 `vctn-blog-web` | 默认播种清单补 blog-web |
| C3 | System Log 无来源 | 10 章要求 5 类日志含 System Log，现有体系有 Application/Access/Security/Operation/Audit，**无 System Log 表** | 需确认：新增 `sys_system_log` 还是由 Application Log 承载 |
| C4 | Alert Resolve 权限边界模糊 | 24 章 `POST /alerts/{id}/resolve` 注"仅系统/受控流程，不允许任意伪造"，但未定义谁能调 | 建议：`OPS_ALERT_MANAGE` 且必须经告警评估流程，人工不得直接置 RESOLVED |
| C5 | Dashboard Widget 模型未冻结 | 19 章说"Widget 类型和布局模型需在 DB/API 设计阶段冻结"，但 Spec 未给出 | 需随 Phase 2 一并冻结 |
| C6 | 权限码需与现有矩阵统一 | 21 章 22 个 `OPS_*` 码 vs 现有 64 条权限矩阵，属**矩阵外新增** | 需登记（同既有 `RUNTIME_EXTRA_PERMISSIONS` 机制） |
| C7 | 遗漏的决策项 | 16 章"HTTP response validation 是否启用及规则"未列入 40 章决策表 | 补为 `OPS-DECISION-013` |
| C8 | Job Retry/Stop 是高风险操作 | 17 章要求，但 010 高风险操作模型未定 | 随 010 一并决策 |
| C9 | Retention 未定但 Phase 5 要验证 | 27 章禁止 AI 设定，42 章要求验证数据生命周期 | 依赖 007 |
| C10 | Metrics 采集不能影响业务库 | 26 章要求，但 001/006 未定 | 依赖 001/006 |

---

## 4 不阻塞、可立即开工的部分

以下与任何 `OPS-DECISION-*` 无关，可在 Phase 1 确认同时并行推进：

1. **工程脚手架**：新建 `vctn-ops-web`（Vue3 + TS + Vite + Pinia + Element Plus + Axios，端口 5176），与 tools/blog 同构
2. **后端模块骨架**：`vctn-api/app/ops/` 15 个子模块目录 + 路由装配（挂载 `/ops`）
3. **权限码登记**：22 个 `OPS_*` 码进入现有 permission/seed 体系
4. **审计集成**：复用 `sys_audit_log`，封装 Ops 审计入口（operator/action/resource/before/after/trace）
5. **非时序表设计**：`ops_environment/host/host_group/service/service_dependency/endpoint/agent/agent_heartbeat/monitor/event/alert_rule/alert/alert_history/alert_notification/notification_channel/notification_group/maintenance_window/availability_check/availability_result/dashboard/dashboard_widget/operation_record`
6. **只读现状类接口**：服务/主机健康状态（读现有探针与心跳，不依赖采集方案）

---

## 5 下一步（待确认）

Phase 1 完成后按 42 章顺序推进：

```text
Phase 1  技术决策（本次等待确认）  ← 当前位置
Phase 2  数据库设计（ER / 字段字典 / 约束索引 / DDL / Alembic migration）
Phase 3  后端（Router + DTO + Service + Repository + Authorization + Error + Trace + Audit + Tests）
Phase 4  前端 vctn-ops-web（22 个页面）
Phase 5  集成验证（Agent→Metrics→Alert→Notification→Audit；API→Trace→Logs；Maintenance 抑制告警）
Phase 6  验证报告（DB / API / Security / Frontend / Test / Known Issues / Remaining Blockers）
```
