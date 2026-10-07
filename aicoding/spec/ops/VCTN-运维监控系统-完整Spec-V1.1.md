# 01 需求总览

## 1.1 产品名称
VCTN 运维监控系统（Ops Monitoring）

## 1.2 目标
为 VCTN 提供统一的系统运行状态、基础设施、服务、API、PostgreSQL、Redis、日志、指标、事件、告警、可用性、Job、Trace 和运维审计能力。

## 1.3 新增项目

```text
D:\project\bmw730\
├── vctn-api
├── vctn-admin-web
├── vctn-tools-web
└── vctn-ops-web
```

## 1.4 域名

```text
admin.xxx.com -> vctn-admin-web
tools.xxx.com -> vctn-tools-web
ops.xxx.com   -> vctn-ops-web
api.xxx.com   -> vctn-api
```

## 1.5 角色
- SUPER_ADMIN：现有超级管理员，拥有全局能力。
- OPS_ADMIN：运维管理员。
- OPS_VIEWER：只读运维人员。

角色最终仍通过现有 RBAC 实现，不新增独立认证体系。

## 1.6 V1 范围
Dashboard、Host、Service、API、PostgreSQL、Redis、Logs、Metrics、Events、Alerts、Alert Rules、Notification、Maintenance、Agent、Availability、Jobs、Trace、Audit、RBAC。

## 1.7 明确不做
Shell、任意 SQL Console、Redis Console、文件管理、自动修复、自动扩缩容、自动部署、Kubernetes Console、云资源管理。


---

# 02 业务目标与范围

## 目标
1. 快速发现故障。
2. 快速定位根因。
3. 统一查看系统健康状态。
4. 统一处理告警。
5. 建立可追踪的运维操作记录。
6. 为后续 SLO/SLA、自动化运维保留扩展能力。

## 范围边界

### Ops 负责
系统、主机、服务、接口、数据库、Redis、日志、指标、事件、告警、Job、可用性、Agent。

### Analytics 负责
PAGE_VIEW、TOOL_EXECUTE、USER_LOGIN 等用户行为。

### Audit 负责
谁创建/修改/删除/确认/静默/执行了什么操作。


---

# 03 总体架构与边界

## 已确定

```text
vctn-ops-web
      |
      v
vctn-api /api/v1/ops
      |
      +-- PostgreSQL
      +-- Redis
      +-- existing logging/tracing/audit
```

后端继续使用模块化单体：

```text
vctn-api/app/ops/
├── dashboard/
├── hosts/
├── services/
├── apis/
├── database/
├── redis/
├── logs/
├── metrics/
├── events/
├── alerts/
├── notifications/
├── agents/
├── availability/
├── jobs/
├── maintenance/
└── audit/
```

## 边界
- 不新增 tenant_id。
- Ops 使用 sys_user。
- 业务用户 biz_user 不直接拥有 Ops 管理权限。
- 不通过内部 HTTP 调用本模块。
- Service 层负责业务事务。
- Repository 不 commit。
- 使用现有 Trace ID / Request ID。


---

# 04 运维对象模型

核心对象：

| 对象 | 说明 |
|---|---|
| Environment | PRODUCTION/STAGING/TEST/DEVELOPMENT |
| Host | 物理机、虚拟机或其他主机 |
| Host Group | 主机分组 |
| Service | 被监控服务 |
| Service Dependency | 服务依赖关系 |
| Endpoint | API/HTTP/TCP/DNS/SSL 等监控目标 |
| Agent | 主机采集 Agent |
| Monitor | 统一监控对象 |
| Metric | 数值指标 |
| Event | 状态变化/系统事件 |
| Alert Rule | 告警规则 |
| Alert | 告警实例 |
| Notification | 通知记录 |
| Maintenance Window | 维护窗口 |
| Dashboard | 仪表盘 |
| Widget | Dashboard 组件 |

对象均需支持状态、标签、时间字段以及必要的软删除策略。

推荐标签：

```json
{
  "environment": "production",
  "region": "us-west",
  "service": "vctn-api",
  "team": "backend"
}
```

最终字段以数据库设计阶段冻结版本为准。


---

# 05 主机监控需求

## 监控对象
- hostname
- IP
- OS
- CPU
- Memory
- Disk
- Network
- Load
- Uptime
- Agent 状态

## 主机状态
建议支持 ONLINE、OFFLINE、UNKNOWN、MAINTENANCE；最终枚举需决策冻结。

## 指标
- CPU 使用率
- Load 1/5/15
- Memory 使用率
- Disk 使用率
- Disk I/O
- Network RX/TX
- Agent heartbeat

## 告警
CPU、Memory、Disk、Load、Network、Host Down。

阈值和持续时间必须配置化，不允许硬编码。


---

# 06 服务监控需求

默认对象：
- vctn-api
- vctn-admin-web
- vctn-tools-web
- vctn-ops-web
- PostgreSQL
- Redis
- Nginx
- 后续 ARQ/Scheduler 等

状态：
UP、DOWN、DEGRADED、UNKNOWN、MAINTENANCE。

每个服务支持：
- 健康状态
- 最近检查时间
- 可用率
- 错误率
- 延迟
- 依赖
- 最近事件
- 最近告警

服务依赖必须支持拓扑展示及根因关联。


---

# 07 API 监控需求

## 指标
- Request Count
- RPS/QPS
- Average Response Time
- P50/P90/P95/P99
- 2xx/3xx/4xx/5xx
- Error Rate
- Slow API
- Trace ID 关联

## 维度
method、path、status_code、service、environment、time window。

## 安全
不得在监控指标中保存：
- Authorization
- Cookie 中敏感信息
- Password
- MFA Secret
- API Key
- JWT 原文

API 路径参数中的敏感值必须按规则脱敏。


---

# 08 PostgreSQL 监控需求

PostgreSQL 已经是 VCTN 既有数据库，Ops 直接监控现有实例/集群。

## 监控
- status
- version
- uptime
- connections
- active/idle/idle-in-transaction
- TPS/QPS
- commits/rollbacks
- locks
- blocked queries
- slow queries
- database size
- table/index size
- cache/hit 等可获得指标

## 安全
不得默认向前端暴露 SQL 参数中的密码、Token、API Key、用户敏感数据。

任意 SQL Console 不属于 V1。


---

# 09 Redis 监控需求

Redis 为现有基础设施。

## 监控
- status
- version
- memory
- hit/miss
- connections
- commands/QPS
- evictions
- slow commands
- keyspace 统计

## 禁止
V1 不提供任意 Redis Key 修改、删除、执行命令能力。


---

# 10 日志中心需求

## 日志类型
- Application Log
- Access Log
- Security Log
- Operation Log
- System Log

## 查询
time、level、service、host、trace_id、request_id、keyword、IP。

## 展示
- 时间线
- 详情
- Trace 跳转
- 上下文日志
- 关联事件/告警

## 脱敏
永不展示：
- password
- MFA secret
- access token
- authorization header
- API key
- 用户上传的敏感原文

日志存储技术不在本文件冻结。


---

# 11 指标中心需求

指标分为：
1. 原始指标
2. 聚合指标
3. 派生指标

至少支持：
- counter
- gauge
- rate
- latency
- availability

维度包括：
host、service、endpoint、environment、region 等。

查询支持：
- 时间范围
- step/粒度
- 聚合
- Top N
- 趋势
- 对比

原始数据保留周期、存储引擎、压缩方式属于 BLOCKER 决策项。


---

# 12 事件中心需求

事件与指标、日志、告警分离。

典型事件：
- service down
- host offline
- agent offline
- job failed
- job timeout
- maintenance started/ended
- deployment/restart（如未来接入）
- alert triggered/resolved

事件支持：
- event_id
- event_type
- source
- resource
- severity
- occurred_at
- metadata
- trace_id/request_id（如有）

事件不得直接等同于告警。


---

# 13 告警中心需求

## 生命周期

```text
NORMAL -> TRIGGERED -> FIRING -> ACKNOWLEDGED -> RESOLVED
```

允许 Silence，不代表 Resolve。

## 严重级别
INFO、WARNING、ERROR、CRITICAL。

## 告警类型
HOST_DOWN、CPU_HIGH、MEMORY_HIGH、DISK_HIGH、DISK_FULL、LOAD_HIGH、NETWORK_ERROR、SERVICE_DOWN、API_ERROR_RATE_HIGH、API_LATENCY_HIGH、DATABASE_DOWN、DATABASE_CONNECTION_HIGH、DATABASE_LOCK_WAIT、REDIS_DOWN、REDIS_MEMORY_HIGH、REDIS_HIT_RATE_LOW、JOB_FAILURE、JOB_TIMEOUT、SSL_EXPIRING、HTTP_CHECK_FAILURE。

## 规则
支持：
- metric
- condition
- threshold
- duration
- severity
- resource/service/host
- notification policy

## 去重
使用稳定 fingerprint 去重。

## 恢复
恢复必须产生 RESOLVED 状态，并按通知策略决定是否通知。

## 根因
支持依赖拓扑关联，避免基础设施故障造成大量重复下游告警。


---

# 14 通知中心需求

通知通道采用抽象接口，不允许业务代码散落 if/else。

候选渠道：
- Email
- Webhook
- WeCom
- DingTalk
- Feishu
- SMS

V1 是否实现哪些渠道属于决策项。

通知记录至少包含：
- notification_id
- alert_id
- channel
- receiver/group
- status
- sent_at
- retry_count
- error_message

通知必须支持失败重试、幂等和审计。


---

# 15 Agent 需求

Agent 负责：
- CPU
- Memory
- Disk
- Network
- Process/host 基础信息
- Heartbeat

Server 负责：
- Agent 注册
- Agent 身份校验
- Agent 状态
- 最后心跳
- 版本
- 升级状态
- 禁用/启用

Agent 状态候选：
ONLINE、OFFLINE、UPGRADING、UNKNOWN。

通信协议目前不冻结。候选：
HTTPS REST、gRPC、WebSocket、MQTT 等。

禁止 Agent 自带高风险远程执行能力。


---

# 16 可用性监控需求

支持：
- HTTP
- TCP
- DNS
- SSL certificate expiry

HTTP 支持：
- status code
- latency
- timeout
- response validation（是否启用及规则需决策）

TCP：
- connect success
- latency

DNS：
- resolve success
- latency

SSL：
- certificate expiry
- issuer
- hostname match

检查结果应形成历史趋势并可触发告警。


---

# 17 Job 监控需求

监控现有：
- sys_job
- sys_job_definition

状态：
RUNNING、SUCCESS、FAILURE、TIMEOUT、CANCELLED 等。

统计：
- success rate
- failure rate
- avg/max duration
- repeated failures
- timeout
- long-running

支持受权限控制的 Retry/Stop 操作。

任何 Job 操作必须写入 Audit。


---

# 18 Trace 关联需求

复用既有：
- X-Trace-ID
- X-Request-ID

关联链路：

```text
Request
 -> API metric
 -> Access/Application Log
 -> Event
 -> Alert
 -> Audit（如有操作）
```

支持从：
- API
- Log
- Alert
- Job
- Event

跳转到 Trace 上下文。

不得要求重新建设另一套 Trace ID。


---

# 19 Dashboard 需求

默认 Dashboard：
- System Overview
- Host
- Service
- API
- PostgreSQL
- Redis
- Tools
- Alerts

Widget 类型候选：
- Stat
- Line
- Area
- Bar
- Table
- Gauge
- Heatmap
- TopN
- Timeline
- Dependency Graph

Dashboard 支持：
- 查询时间范围
- 自动刷新
- Widget 排序
- 权限控制

自定义 Dashboard 的编辑能力属于 V1 范围，但 Widget 类型和布局模型需在 DB/API 设计阶段冻结。


---

# 20 维护窗口需求

支持：
- 创建
- 修改
- 删除
- 启用/禁用
- 时间范围
- 作用对象
- 原因
- 创建人

维护窗口期间：
- 可抑制相关告警通知
- 不应篡改原始指标/事件
- 状态变化必须可追踪

创建、修改、删除、静默等必须 Audit。


---

# 21 权限与安全

复用现有 RBAC。

建议权限：
- OPS_DASHBOARD_VIEW
- OPS_HOST_VIEW
- OPS_HOST_MANAGE
- OPS_SERVICE_VIEW
- OPS_SERVICE_MANAGE
- OPS_API_VIEW
- OPS_DATABASE_VIEW
- OPS_REDIS_VIEW
- OPS_LOG_VIEW
- OPS_ALERT_VIEW
- OPS_ALERT_MANAGE
- OPS_ALERT_ACK
- OPS_ALERT_SILENCE
- OPS_AGENT_VIEW
- OPS_AGENT_MANAGE
- OPS_MONITOR_VIEW
- OPS_MONITOR_MANAGE
- OPS_JOB_VIEW
- OPS_JOB_MANAGE
- OPS_DASHBOARD_MANAGE
- OPS_MAINTENANCE_MANAGE
- OPS_AUDIT_VIEW

最终权限编码必须与现有 permission/resource 模型统一。

高风险操作默认禁止。
所有权限由后端 AuthorizationService 强制执行。


---

# 22 审计需求

复用现有 `sys_audit_log`。

必须审计：
- Monitor 创建/修改/删除
- Alert ACK
- Alert Silence
- Alert Rule 修改
- Notification 配置修改
- Maintenance 修改
- Agent 启停/禁用等管理
- Job Retry/Stop
- Dashboard 管理
- 其他 Ops 配置变更

审计至少记录：
operator、action、resource、before、after、result、error、IP、UA、trace_id、request_id、created_at。

Audit append-only。


---

# 23 前端页面需求

项目：
`D:\project\bmw730\vctn-ops-web`

技术：
Vue 3 + TypeScript + Vite + Vue Router + Pinia + Element Plus + Axios。

页面：
1. 登录/会话
2. Dashboard
3. Hosts
4. Host Detail
5. Services
6. Service Detail
7. APIs
8. API Detail
9. PostgreSQL
10. Redis
11. Logs
12. Metrics
13. Events
14. Alerts
15. Alert Rules
16. Notifications
17. Maintenance
18. Agents
19. Availability
20. Jobs
21. Dashboards
22. Ops Audit

要求：
- 路由来自权限模型
- 菜单来自后端
- Button/API 权限前后端双重控制，后端为最终权威
- 所有列表统一分页
- 所有请求携带 Trace/Request 标识
- 敏感信息脱敏


---

# 24 API 需求

Base：

`/api/v1/ops`

## Dashboard
GET `/overview`

## Hosts
GET `/hosts`
GET `/hosts/{id}`
POST `/hosts`
PUT `/hosts/{id}`
DELETE `/hosts/{id}`

## Services
GET `/services`
GET `/services/{id}`
POST `/services`
PUT `/services/{id}`
DELETE `/services/{id}`

## APIs
GET `/apis`
GET `/apis/{id}`
GET `/apis/{id}/metrics`

## Metrics
GET `/metrics`
GET `/metrics/series`

## Logs
GET `/logs`
GET `/logs/{id}`

## Events
GET `/events`
GET `/events/{id}`

## Alerts
GET `/alerts`
GET `/alerts/{id}`
POST `/alerts/{id}/ack`
POST `/alerts/{id}/silence`
POST `/alerts/{id}/resolve`（仅系统/受控流程，不允许任意伪造）

## Alert Rules
GET `/alert-rules`
POST `/alert-rules`
PUT `/alert-rules/{id}`
DELETE `/alert-rules/{id}`

## Notifications
GET `/notifications`
GET `/notification-channels`
POST `/notification-channels`
PUT `/notification-channels/{id}`

## Agents
GET `/agents`
GET `/agents/{id}`
POST `/agents/{id}/enable`
POST `/agents/{id}/disable`

## Availability
GET `/availability`
POST `/availability`
PUT `/availability/{id}`
DELETE `/availability/{id}`

## Jobs
GET `/jobs`
GET `/jobs/{id}`
POST `/jobs/{id}/retry`
POST `/jobs/{id}/stop`

## Maintenance
GET `/maintenance`
POST `/maintenance`
PUT `/maintenance/{id}`
DELETE `/maintenance/{id}`

## Dashboards
GET `/dashboards`
GET `/dashboards/{id}`
POST `/dashboards`
PUT `/dashboards/{id}`
DELETE `/dashboards/{id}`

实际 DTO、状态码、分页结构、幂等策略必须与现有 API Spec 一致。


---

# 25 数据模型需求

以下是候选表，不是最终 DDL：

- ops_environment
- ops_host
- ops_host_group
- ops_service
- ops_service_dependency
- ops_endpoint
- ops_agent
- ops_agent_heartbeat
- ops_monitor
- ops_metric_definition
- ops_metric_sample
- ops_metric_hourly
- ops_metric_daily
- ops_event
- ops_alert_rule
- ops_alert
- ops_alert_history
- ops_alert_notification
- ops_notification_channel
- ops_notification_group
- ops_maintenance_window
- ops_availability_check
- ops_availability_result
- ops_dashboard
- ops_dashboard_widget
- ops_operation_record

要求：
- BIGINT + Snowflake
- UTC/TIMESTAMPTZ
- PostgreSQL
- JSONB 用于结构化扩展属性
- FK/UNIQUE/CHECK/INDEX 必须经过设计评审
- 不新增 tenant_id
- 不在本 Spec 中冻结最终字段


---

# 26 性能与容量需求

系统应支持：
- Dashboard 查询在正常数据量下稳定响应
- 告警计算不能阻塞 API 请求
- 指标采集不能影响业务数据库
- 日志查询必须分页
- 大时间范围查询必须限制粒度或使用聚合
- 导出必须异步
- 高基数指标必须受到控制
- 所有采集端必须有超时、重试、退避和限流机制

具体 TPS、P95、数据量、主机数、指标数、保留量属于容量决策项，不由 AI 猜测。


---

# 27 数据保留需求

现有业务日志保留：
- Access Log 30d
- Security Log 180d
- Operation Log 180d
- Audit Log 2y
- Application Log 30d

Ops 新增：
- Metrics 原始数据：待确认
- Metrics 聚合数据：待确认
- Events：待确认
- Alert History：建议长期可查询，具体周期待确认
- Availability Result：待确认

禁止 AI 自行设定最终 retention。


---

# 28 扩展性需求

未来允许：
- 更多 Agent
- 更多通知渠道
- 更多指标类型
- 更多探针
- SLO/SLA
- 自动化运维
- Kubernetes
- 云资源
- 专业 Metrics/Logs 存储

扩展必须基于接口/Provider/Registry，而不是大量 if/else。

例如：
MetricStorageProvider
AgentTransport
NotificationChannel
AlertEvaluator
LogStorageProvider
ProbeProvider


---

# 29 非功能需求

- 安全优先
- 可审计
- 可追踪
- 可扩展
- 可观测
- 数据脱敏
- 后端权限最终权威
- 不泄露敏感凭据
- 失败可重试
- 操作幂等
- 并发安全
- 时区统一 UTC
- API 统一响应结构
- X-Trace-ID / X-Request-ID 全链路传递


---

# 30 验收标准

## 功能
- Dashboard 正常
- Host/Service/API 状态可查看
- PostgreSQL/Redis 可监控
- Logs 可检索
- Metrics 可查询
- Events 可查看
- Alert 可触发、ACK、Silence、Resolve
- Notification 可记录发送结果
- Agent 可注册/心跳/离线检测
- Availability 可执行
- Job 可监控并受权限控制
- Trace 可关联
- Dashboard 可配置
- Audit 完整

## 安全
- 无未授权接口可调用
- 无敏感信息泄露
- 无任意 SQL/Redis/Shell
- 所有高风险操作有权限+Audit

## 工程
- 无 TODO/NotImplementedError/pass 占位
- 无未冻结依赖
- migration 可重复升级
- 不破坏现有表
- API/Model/Repository/Service/Test 完整

## BLOCKER
任何未决 `OPS-DECISION-*` 不得被 AI 自行选择。


---

# 31 技术方案候选

本文件仅列候选，不代表冻结。

## Metrics
PostgreSQL 普通表、PostgreSQL 分区、TimescaleDB、Prometheus、VictoriaMetrics 等。

## Logs
现有 PostgreSQL、Loki、OpenSearch/Elasticsearch 等。

## Agent
HTTPS REST、gRPC、WebSocket、MQTT。

## Realtime
Polling、SSE、WebSocket。

## Scheduler
现有 APScheduler/ARQ、独立调度器、其他方案。

## Alert
自研规则引擎、Prometheus Alertmanager 等。

## Notification
自研 Provider、第三方消息服务等。

选择必须基于容量、安全、维护成本、与现有架构匹配度进行评估。


---

# 32 Metrics 存储方案对比

| 方案 | 优点 | 缺点 | 适合 |
|---|---|---|---|
| PostgreSQL 普通表 | 简单、无新增基础设施 | 大规模时压力明显 | 小规模 V1 |
| PostgreSQL 分区 | 复用 PG、生命周期较好 | 设计复杂度增加 | 中小规模 |
| TimescaleDB | 时间序列能力强 | 增加扩展依赖 | PG 体系下中大型 |
| Prometheus | 监控生态成熟 | 与业务 PG 体系不同 | 专业监控 |
| VictoriaMetrics | 高性能、成本较好 | 增加组件 | 较大规模 |

**结论：不冻结。**

决策依据必须包括：主机数、指标数、采集间隔、保留期、查询并发、运维成本。


---

# 33 Logs 存储方案对比

| 方案 | 优点 | 缺点 |
|---|---|---|
| PostgreSQL | 复用现有体系 | 日志规模大时成本高 |
| Loki | 与监控生态结合好 | 查询模型不同 |
| OpenSearch/Elasticsearch | 检索强 | 运维成本高 |
| 其他 | 可按规模选择 | 需要评估 |

**不冻结。**

现有业务日志体系必须优先复用，除非容量/检索需求证明需要独立日志存储。


---

# 34 Agent 通信方案对比

| 方案 | 优点 | 缺点 |
|---|---|---|
| HTTPS REST | 简单、成熟 | 高频指标效率一般 |
| gRPC | 性能和协议明确 | 运维复杂度增加 |
| WebSocket | 双向实时 | 长连接治理 |
| MQTT | IoT/Agent 友好 | 引入 Broker |

安全必须包含身份认证、重放防护、证书/密钥管理、权限和审计。

**不冻结。**


---

# 35 实时通信方案对比

候选：
- Polling
- SSE
- WebSocket

评估：
- 实时性
- 浏览器兼容
- 服务端连接数
- Redis/消息系统依赖
- 断线重连
- 运维复杂度

**不冻结。**


---

# 36 调度与采集方案对比

候选：
- 现有 APScheduler
- 现有 ARQ
- 专用 Scheduler
- Agent 主动 Push

原则：
- 不让采集任务阻塞 API
- 支持超时、重试、退避
- 采集任务可观测
- 防止重复采集
- 不能因为监控故障拖垮业务系统

**不冻结。**


---

# 37 告警引擎方案对比

候选：
1. 自研规则计算
2. Prometheus Alertmanager 体系
3. 其他专业告警引擎

必须评估：
- Rule DSL
- duration
- dedup
- grouping
- silence
- inhibition
- recovery
- HA
- 运维成本

**不冻结。**


---

# 38 通知方案对比

候选：
- 内置 Provider
- 第三方通知平台
- Webhook 自定义

通道：
Email / Webhook / WeCom / DingTalk / Feishu / SMS。

必须支持失败重试、幂等、限流、审计和敏感配置加密。

**不冻结。**


---

# 39 方案评估矩阵

统一评分维度：

| 维度 | 权重建议 |
|---|---:|
| 与现有 VCTN 架构匹配 | 20% |
| 性能 | 20% |
| 可扩展性 | 15% |
| 稳定性 | 15% |
| 运维复杂度 | 15% |
| 成本 | 10% |
| 安全 | 5% |

最终权重和结论需要在方案评审时确认。

禁止 Agent 根据“建议权重”自动完成最终选择。


---

# 40 待确认决策项

以下均为 BLOCKER：

| ID | 决策 | 当前状态 |
|---|---|---|
| OPS-DECISION-001 | Metrics 存储 | 待确认 |
| OPS-DECISION-002 | Agent 通信 | 待确认 |
| OPS-DECISION-003 | 实时推送 | 待确认 |
| OPS-DECISION-004 | Logs 存储 | 待确认 |
| OPS-DECISION-005 | Alert Engine | 待确认 |
| OPS-DECISION-006 | Metrics 采集周期 | 待确认 |
| OPS-DECISION-007 | Metrics retention | 待确认 |
| OPS-DECISION-008 | Alert 默认阈值 | 待确认 |
| OPS-DECISION-009 | Notification V1 渠道 | 待确认 |
| OPS-DECISION-010 | 高风险操作模型 | 待确认 |
| OPS-DECISION-011 | SLO/SLA 目标 | 待确认 |
| OPS-DECISION-012 | 容量基线 | 待确认 |

### 已确认
- PostgreSQL：现有基础设施，已确定。
- Redis：现有基础设施，已确定。
- FastAPI：现有后端。
- Vue 3 + TypeScript：现有前端技术体系。
- 单 FastAPI 模块化单体：已确定。


---

# 41 AI Coding 开发约束

## 强制
1. 项目根目录只能是 `D:\project\bmw730`。
2. 新增 `vctn-ops-web`。
3. 后端只在现有 `vctn-api/app/ops/` 扩展。
4. PostgreSQL/Redis 复用现有基础设施。
5. 不增加 tenant_id。
6. 不新增独立认证系统。
7. 不自行添加依赖。
8. 未冻结技术方案不得实现。
9. 不修改现有业务模块的既有行为，除非 Spec 明确要求。
10. 所有接口必须通过 AuthorizationService。
11. 所有配置变更和运维动作必须 Audit。
12. 不允许 Shell/任意 SQL/任意 Redis 命令。
13. 不记录密码、MFA Secret、Token、API Key 等敏感信息。
14. 不使用 `if channel == ...` 构建通知系统，使用 Provider/Registry。
15. 不使用 `if tool == ...` 类似方式构建可扩展监控类型。
16. Service 负责事务，Repository 不 commit。
17. API 统一 `/api/v1/ops`。
18. API 统一响应结构。
19. Trace/Request ID 全链路。
20. 没有测试的功能不得宣称完成。

## BLOCKER 行为

遇到 `OPS-DECISION-*`：
- 停止对应实现；
- 输出 BLOCKER；
- 列出需要确认的选项；
- 不允许猜测。

## 禁止
- TODO
- NotImplementedError
- 空 pass 作为功能实现
- Mock 永久留在生产代码
- 直接 CREATE TABLE 大 SQL 代替规范 Alembic migration
- 删除现有业务表


---

# 42 实施阶段与验证

## Phase 0
需求审查。

输出：
- requirements review
- contradiction list
- blocker list

## Phase 1
技术方案决策。

必须完成：
OPS-DECISION-001 ~ 012 中所有实现相关项。

## Phase 2
数据库设计。

输出：
- ER
- field dictionary
- constraints
- indexes
- DDL
- Alembic migration

## Phase 3
Backend。

每个模块：
Router + DTO + Service + Repository + Authorization + Error Mapping + Trace + Audit + Tests。

## Phase 4
Frontend。

完成：
- 路由
- 页面
- API client
- Pinia
- 权限
- 状态
- 图表/表格
- 空/错/加载状态

## Phase 5
Integration。

验证：
- Agent → Metrics
- Metrics → Alert
- Alert → Notification
- Alert → Audit
- API → Trace → Logs
- Job → Ops
- Maintenance → Alert suppression

## Phase 6
Verification。

### 数据库
- migration upgrade
- downgrade
- upgrade
- schema diff
- indexes/constraints

### API
- 正常
- 参数错误
- 未登录
- 无权限
- 越权
- 并发
- 幂等

### Security
- 敏感信息
- 权限绕过
- Agent 身份
- 重放攻击
- 高风险接口

### Frontend
- 权限菜单
- 无权限页面
- API error
- realtime reconnect（如采用）
- large dataset pagination

最终输出：
1. Verification Report
2. API Inventory
3. DB Verification Report
4. Security Report
5. Test Report
6. Known Issues
7. Remaining Blockers


---

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
