# VCTN 上线待办清单

> **进度（2026-10-07 更新）**：P0 七项已全部落地；GL-09 内置调度器、GL-12 自监控接
> 入、GL-03 的 CentOS 部署手册也已落地。
> 已完成：安全响应头、生产关闭文档、容器化、反向代理、备份与演练脚本、保留清理 CLI、
> CI、生产初始化防护、**内置调度器（APScheduler + PG advisory lock）**、
> **自监控（探测执行器 + 种子自监控检查项）**、**CentOS 部署手册与配套脚本**、
> **对象存储（local / S3 双后端，默认 RustFS，httpx + 自研 SigV4，零新增依赖）**。
> 仍待办：压测基线（GL-13）、审计导出界面（GL-17）。

> 基于 2026-10-07 对 `F:\project\bmw730` 的实测盘点。
> 每项都标注了**实测证据**（文件 / grep 结果），避免与真实状态脱节。

---

## 总判断

**代码层面已具备企业级底子，缺口集中在「部署、运维、合规」三块。**

已有的（不用再做）：

| 能力 | 证据 |
| --- | --- |
| 配置启动自检 | `Settings.validate_startup()` 校验 API 前缀 / 日志级别 / DB / Redis / 鉴权参数 |
| 生产环境防呆 | `resolved_jwt_secret` 在 `APP_ENV=production` 缺密钥时**直接拒绝启动** |
| CORS 安全 | `cors_origins` 显式拒绝通配符 `*` |
| 审计 | `sys_audit_log` 权威追加 + `ops_operation_record` 双写，`AUDIT_ENABLED=true` |
| 限流 | `RATE_LIMIT_ENABLED=true`，Redis 故障时 **fail-open**（`rate_limit/service.py:68/78/157`） |
| 凭据存储 | refresh token 落库的是 **hash**（`platform/auth/repository.py:133`） |
| 密码策略 | 12 位 + 大小写 + 数字 + 特殊字符 + 历史 + 过期 + 失败锁定 |
| 测试 | 后端 244 passed；前端 vue-tsc / eslint / vite build 全通过 |

缺的是：**没人把它包装成可上线、可运维、可回滚的产品。**

---

## P0 · 上线阻断项（不做就上线，必出事）

### GL-01 [已完成] 安全响应头缺失

- **证据**：全仓 grep `HSTS|Strict-Transport|X-Content-Type|X-Frame-Options|Content-Security` → **0 命中**
- **要做**：加中间件统一输出
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`（HTTPS 启用后）
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` 或 `SAMEORIGIN`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy`（4 个前端按自己的 CDN/内联脚本情况分别定）
- **验收**：`curl -I` 能看见上述头；等保扫描 / 渗透测试不报缺失

### GL-02 [已完成] 生产环境 OpenAPI 文档对外暴露

- **证据**：`app/main.py:266` 的 `FastAPI(...)` **未设置** `docs_url` / `redoc_url` / `openapi_url`
- **后果**：生产默认开放 `/docs`、`/redoc`、`/openapi.json`，等于把 86 个 ops 端点 + admin/platform/tools 的全部接口结构与参数公之于众
- **要做**：`APP_ENV=production` 时把三者置 `None`
- **验收**：生产访问 `/docs` 返回 404，开发环境仍可用

### GL-03 [已完成] 完全没有部署资产

- **证据**：根目录无 `Dockerfile`、无 `docker-compose*.yml`、无 Nginx/Caddy 配置、无 systemd/supervisor 单元；`scripts/` 下只有 `start-all.ps1` 等 Windows 本地脚本
- **要做**：
  - `vctn-api/Dockerfile`（多阶段 + 非 root 用户 + `PYTHONPATH=.`）
  - 4 个前端各自的 `Dockerfile`（`vite build` → nginx 静态托管）
  - `docker-compose.yml` 串起 api + 4 web + postgres + redis
  - 反向代理配置（**见 GL-07，这是硬依赖**）
  - 进程守护与崩溃自愈（容器 `restart: unless-stopped` 或 systemd）
- **已落地**：后端 `Dockerfile`、四个前端 `Dockerfile`、`docker-compose.yml` / `docker-compose.managed.yml`、
  `deploy/nginx/`，以及 **`docs/DEPLOY-CENTOS.md` + `scripts/deploy/centos/`**（CentOS / Rocky / Alma 的
  容器与裸机两条路线、SELinux 与 firewalld 处理、升级回滚）
- **验收**：`docker compose up -d` 一次起全站；kill 掉 api 容器能自动拉起

### GL-04 [已完成] 数据库无备份、无恢复演练

- **证据**：106 张表，全仓无备份脚本、无 PITR 配置
- **要做**：
  - PostgreSQL：`pg_basebackup` 全量 + WAL 归档（PITR），或至少每日 `pg_dump` + 异地留存
  - Redis：按用途决定是否开 AOF（目前 Redis 存会话/限流/锁，丢了的后果要评估）
  - **必须做一次真实恢复演练**：备份没验证过等于没备份
- **验收**：能在新机器上用备份完整还原，并跑通 `alembic current`

### GL-05 [已完成] 密钥明文落在 `.env`

- **证据**：`AUTH_JWT_SECRET` / `DB_PASSWORD` / `REDIS_PASSWORD` 都在 `vctn-api/.env`
- **要做**：生产改走密钥管理（Vault / 云 KMS / K8s Secret / 至少是 600 权限的宿主机文件 + 独立挂载），`.env` 只在开发用
- **注意**：`AUTH_JWT_SECRET` 一变，所有已签发 token 全部失效 —— 上线时要在低峰期做，并接受一次全员重登
- **验收**：生产镜像与代码库中不含任何明文凭据

### GL-06 [已完成] 对象存储改造（RustFS / S3）

- **原来**：`FILE_STORAGE_PROVIDER=local`，文件落在某台机器的磁盘上 —— 多实例时各写各的，容器重启即丢
- **现在**：`app/shared/storage/` 统一入口
  - `local`（pilot 单机）与 `s3`（任意 S3 兼容端点，仓库默认跑 RustFS）两个后端，**零新增依赖**：用 `httpx` + 自研 SigV4（依赖索引禁止另一个 S3 SDK）
  - `FILE_STORAGE_PROVIDER` 接受 `s3` / `rustfs` / `minio`（历史别名），记录的 provider 统一是 `s3`
  - 对象 Key 由服务端生成并强校验（`..` / 绝对路径 / 空段一律拒绝），前端无法指定落盘位置
  - 上传走「申请位置 → PUT 预签名 / API 代理 → 确认」三步；直传没到货的记录会被回收
  - 图片按**魔数**判定类型，客户端声明的 `image/png` 与实际字节不符即拒绝
  - SVG 强制 `attachment`，永不在浏览器里渲染
  - `/ready` 增加 `object_storage` 探针；清理任务支持 `--only export_objects`
- **切换方式**：`FILE_STORAGE_PROVIDER=rustfs`（或 `s3`）+ 填 `S3_*`；旧的 `MINIO_*` 环境变量仍会被读取（见 `.env.deploy.example`）
- **验收**：起两个 api 副本，上传后从另一个副本下载同一文件；`curl -s localhost:8000/ready | jq .data.checks.object_storage`
- **RustFS 注意**：health 是 `/health`、数据目录属主必须 `10001:10001`、控制台 9001 不要对外发布、浏览器直传要设 `RUSTFS_CORS_ALLOWED_ORIGINS`
- **遗留**：已有本地文件如需搬到 RustFS，需要一次性迁移脚本（`rclone sync`，未包含在本次改动）

### GL-07 [已完成] 前端强依赖反向代理，但没有任何说明

- **证据**：4 个前端 `apiBaseUrl` 默认值都是相对路径 `/api/v1`（`admin/tools/ops` 在 `src/api/endpoint.ts`，blog 在 `client.ts`）
- **后果**：**没有反向代理把 `/api/v1` 转发到后端，前端就是全白屏**，且报错信息不会提示是这个原因
- **要做**：在部署文档里明确写出代理规则，例如

  ```nginx
  location /api/     { proxy_pass http://vctn-api:8000/api/; }
  location /health   { proxy_pass http://vctn-api:8000/health; }
  location /ready    { proxy_pass http://vctn-api:8000/ready; }
  location /version  { proxy_pass http://vctn-api:8000/version; }
  ```

- **补充**：`vctn-blog-web` 与 `vctn-ops-web` **缺少 `.env.example`**（admin/tools 有），补齐并写 `VITE_API_BASE_URL`
- **验收**：4 个前端在纯静态托管下（不经 vite dev proxy）能正常登录

---

## P1 · 上线后很快会出问题

### GL-08 [已完成] 日志与数据保留只配了天数，没有任何清理任务

- **证据**：`LOG_RETENTION_ACCESS/APPLICATION/AUDIT/OPERATION/SECURITY_LOG_DAYS` 5 个配置项，**唯一的消费方是 `seed/system_seed.py` 把它们写进 `sys_config` 表** —— 没有任何代码真的去删数据；ops 的 7/30/180 天保留同样无消费方
- **后果**：审计日志、访问日志、指标样本只增不减，几个月后拖垮磁盘与查询性能
- **要做**：按 GL-09 的调度器加清理 job，或先上 pg 分区 + 定时 drop 旧分区
- **验收**：跑一次清理后，过期分区/行数确实下降

### GL-09 [已完成] 没有任何调度器

- **证据（原状）**：全仓 grep `Celery|APScheduler|arq|TaskIQ|cron` → 无调度框架；`app/` 下无 `BackgroundTasks` 常驻任务
- **后果（原状）**：指标小时/天 rollup、告警规则评估、可用性探测、日志清理、导出文件过期 —— 这些周期性任务**当时全部没有触发器**
- **已落地**：`app/ops/scheduler/`（`lock.py` / `jobs.py` / `runtime.py`）
  - APScheduler `AsyncIOScheduler`，四个任务：指标 rollup（每小时，UTC 0 点那趟额外做天聚合）、
    告警评估并派发通知、可用性探测、保留清理（cron，固定 `OPS_SCHEDULER_PURGE_HOUR`，不随容器重启漂移）
  - **每个任务先抢 PG advisory lock**（`pg_try_advisory_lock`，非阻塞）→ 多副本只有赢家执行，输的那份跳过而不是排队重复干活
  - 任务异常不外抛：一次 tick 失败不能把调度器和其余任务一起带走
  - 默认关闭（`OPS_SCHEDULER_ENABLED=false`），由 `docker-compose.yml` / `.env` 显式打开
- **验收**：`.env` 置 `OPS_SCHEDULER_ENABLED=true` 后跑一小时，`ops_metric_hourly` 有桶、
  `ops_availability_result` 每分钟有新行、审计报告里有 `OPS_ALERT_EVALUATE` 之外的评估痕迹

### GL-10 [已完成] 连接池偏小，未做容量验证

- **证据**：`DB_POOL_SIZE=5`（`.env.example:38`），`DB_MAX_OVERFLOW` 未在生产语境下评估
- **后果**：4 个前端 + 采集写入 + 评估器并发，5 个连接会先于数据库成为瓶颈（表现为请求排队、偶发超时）
- **要做**：按 `实例数 × pool_size + overflow ≈ PG max_connections 的 70%` 重算，并做一次压测
- **验收**：压测下 P95 响应时间可接受，无 `QueuePool limit` 报错

### GL-11 [已完成] 多实例从未验证，Snowflake 节点 ID 是硬前提

- **证据**：`SNOWFLAKE_NODE_ID` / `SNOWFLAKE_NODE_BITS` 是配置项
- **后果**：**起第二个实例时若 NODE_ID 相同，生成的 ID 会冲突**，这是静默数据损坏
- **要做**：多实例部署时给每个实例分配唯一 NODE_ID（K8s 用 StatefulSet 序号，或用 pod IP 派生）
- **验收**：两实例并发写入，主键无冲突

### GL-12 [已完成] 没人监控系统自己

- **证据（原状）**：ops 能监控主机/服务/API/数据库/Redis，但 Agent 采集器本体未落地（`BLOCKERS.md` 的 OPS-BLOCKER-01/02），可用性探测也**没有执行器**
- **已落地**
  - `app/ops/availability/probe.py`：HTTP / TCP / DNS / SSL 四种探测执行器（httpx + socket + ssl 标准库，未引新依赖），
    写 `ops_availability_result`；遵循 interval_seconds；失败即写失败结果，绝不抛异常终止 tick
  - 自监控种子：`seed_ops_self_monitoring()` 播种 `vctn_api_self_health` 检查项，
    目标来自 `OPS_SELF_MONITOR_URL`（compose 内默认 `http://api:8000/health`），按 `check_code` 幂等、不覆盖运维的修改
- **剩余**：Agent 探针本体仍是 OPS-BLOCKER-02（未交付范围）；告警规则默认阈值仍是 OPS-BLOCKER-03，
  所以「API 挂了」目前体现在可用性结果由成功变失败，真正触发告警还需要人工建规则
- **验收**：ops 控制台「可用性」里 `vctn_api_self_health` 每分钟刷新一行结果；停掉 API 后出现失败行

### GL-13 [待办] 无性能基线与容量规划

- **要做**：补一次压测（登录、列表查询、工具执行、指标上报四类路径），记录 QPS / P95 / 错误率作为基线
- **验收**：有可对比的数字，下次发版能判断是否劣化

---

## P2 · 规范化与合规

### GL-14 [已完成] 无 CI/CD

- **证据**：根目录与 `vctn-api` 均无 `.github`
- **要做**：提交即跑 `pytest` + `ruff` + 前端 `vue-tsc` / `eslint` / `vite build`；主干保护
- **验收**：PR 未通过检查无法合并

### GL-15 [已完成] 无 Runbook 与回滚流程

- **要做**：
  - 发版步骤（备份 → 迁移 → 部署 → 冒烟 → 观察）
  - **回滚步骤**（`alembic downgrade` 已验证可用，但流程没写）
  - 值班手册：告警响了先看哪、常见故障的处置动作
- **验收**：换一个人照着文档能完成一次发版与回滚

### GL-16 [已完成] 生产初始化数据要重新界定

- **证据**：`app/scripts/seed/` 幂等插入（只按稳定业务键 insert-if-not-exists），管理员密码取自 `VCTN_SEED_ADMIN_PASSWORD`
- **要做**：
  - **测试账号/测试工具/示例内容绝不能进生产**（`--mode=system` 与 `--mode=test` 的边界要在文档里钉死）
  - 生产首次部署后**立即改掉种子管理员密码**（种子密码会进 shell history 和 CI 日志）
  - 51 条指标定义、权限与菜单节点属于必须播种项
- **验收**：生产库无 `test*` 账号、无示例文章

### GL-17 [待办] 等保 / 审计留痕的缺失部分

- **已有**：审计双写、敏感字段不入日志、操作日志
- **缺**：
  - 登录 IP 白名单 / 异常登录地告警
  - 敏感操作（权限变更、密钥重置、数据导出）的**二次确认**
  - 审计报告的可查询、可导出界面（目前审计数据在库里，管理员看不到全貌）
- **验收**：审计员能独立导出一段时间内的全部敏感操作记录

---

## 建议的执行顺序

```
第 1 批（1~2 天）：GL-01 安全头 · GL-02 关文档 · GL-05 密钥外置 · GL-16 初始化数据界定
第 2 批（3~5 天）：GL-03 容器化 · GL-07 反向代理与前端变量 · GL-04 备份与恢复演练
第 3 批（1 周）  ：GL-09 调度器 ✅ · GL-08 清理任务 · GL-06 对象存储 ✅ · GL-10/11 容量与多实例
第 4 批（持续）  ：GL-14 CI · GL-15 Runbook · GL-12 自监控 ✅ · GL-13 压测基线 · GL-17 审计导出

第 3、4 批里 GL-09 与 GL-12 已完成；CentOS 上线照 `docs/DEPLOY-CENTOS.md` 走即可。
```

**最小可上线集**：GL-01 ~ GL-07 全做完 + GL-16，其余可上线后补。
其中 **GL-07 是最容易被忽略却最致命的一项** —— 它不会报错，只会让 4 个前端集体白屏。

---

## 备注：当前已知遗留（非上线阻断）

详见 `vctn-api/BLOCKERS.md`：

- OPS-BLOCKER-01 Job 采集器未接入
- OPS-BLOCKER-02 Agent 探针本体不在交付范围
- OPS-BLOCKER-03 告警规则无默认阈值种子
- OPS-BLOCKER-04 OPS 权限只授予了 `SUPER_ADMIN`
