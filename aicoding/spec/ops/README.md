# VCTN 运维监控系统完整开发 Spec V1.1

> 文档性质：需求冻结 + 技术方案候选 + 开发约束  
> 项目根目录：`D:\project\bmw730`  
> 新增前端：`vctn-ops-web`  
> 后端：继续使用现有 `vctn-api`，新增 `app/ops/` 模块  
> 数据库：现有 PostgreSQL（已确定）  
> 缓存：现有 Redis（已确定）

## 重要原则

1. 本 Spec 冻结业务需求，但**不擅自冻结尚未确认的技术实现方案**。
2. PostgreSQL、Redis、FastAPI、Vue 3 + TypeScript 属于现有项目既定基础设施。
3. Metrics、Logs、Agent 通信、实时推送、告警引擎等实现方案必须在决策项中明确后才能进入实现。
4. AI Coding Agent 不得自行选择 BLOCKER 方案。
5. 任何未冻结项必须标记 `BLOCKER`，遇到 BLOCKER 必须停止对应实现。
6. 运维监控、用户行为分析、审计日志三者必须保持边界：
   - Analytics：用户做了什么；
   - Ops：系统运行得怎么样；
   - Audit：谁改变了什么。
7. 不新增 `tenant_id`。
8. 不把 Ops 单独拆成微服务；当前保持 FastAPI 模块化单体。
9. 不允许通过 shell、任意 SQL、Redis 任意 Key 修改等方式提供高风险运维能力。

## 目录

- 01-需求总览.md
- 02-业务目标与范围.md
- 03-总体架构与边界.md
- 04-运维对象模型.md
- 05-主机监控需求.md
- 06-服务监控需求.md
- 07-API监控需求.md
- 08-PostgreSQL监控需求.md
- 09-Redis监控需求.md
- 10-日志中心需求.md
- 11-指标中心需求.md
- 12-事件中心需求.md
- 13-告警中心需求.md
- 14-通知中心需求.md
- 15-Agent需求.md
- 16-可用性监控需求.md
- 17-Job监控需求.md
- 18-Trace关联需求.md
- 19-Dashboard需求.md
- 20-维护窗口需求.md
- 21-权限与安全.md
- 22-审计需求.md
- 23-前端页面需求.md
- 24-API需求.md
- 25-数据模型需求.md
- 26-性能与容量需求.md
- 27-数据保留需求.md
- 28-扩展性需求.md
- 29-非功能需求.md
- 30-验收标准.md
- 31-技术方案候选.md
- 32-Metrics存储方案对比.md
- 33-Logs存储方案对比.md
- 34-Agent通信方案对比.md
- 35-实时通信方案对比.md
- 36-调度与采集方案对比.md
- 37-告警引擎方案对比.md
- 38-通知方案对比.md
- 39-方案评估矩阵.md
- 40-待确认决策项.md
- 41-AI-Coding开发约束.md
- 42-实施阶段与验证.md
