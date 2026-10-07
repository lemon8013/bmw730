# VCTN 运维手册（Runbook）

面向值班与发版人员。所有命令都在仓库根目录执行。

---

## 1. 拓扑

```
                ┌──────────── gateway (nginx, 80/443) ────────────┐
浏览器 ────────►│  admin.*  tools.*  www.*  ops.*      api.*      │
                └───┬──────────┬────────┬───────┬─────────┬───────┘
                    │          │        │       │         │
                 web-admin  web-tools web-blog web-ops   api:8000
                                                            │
                                              ┌────────────┴───────────┐
                                           postgres:5432          redis:6379
```

- `gateway` 是唯一对外入口；四个前端与 API 都不直接暴露端口。
- 每个前端都把 `/api/` 反代到 `api`，所以前端页面的 API 请求是**同源**的——这是 `apiBaseUrl` 默认值为相对路径 `/api/v1` 的原因。
- 系统探针 `/health` `/ready` `/version` 在根路径，不在 `/api/v1` 下。

## 2. 首次上线

```bash
cp deploy/.env.deploy.example .env      # 填写真实值
# 四个前端各构建一次（产物在各自 dist/）
for d in admin tools blog ops; do (cd vctn-$d-web && npm ci && npm run build); done

docker compose run --rm api migrate     # 建表
docker compose run --rm api seed --mode=system   # 权限、菜单、指标目录
docker compose up -d
docker compose ps                       # 全部 healthy 才算起来
```

上线后**立刻**做的事：

1. 改掉种子管理员密码（种子密码经过 shell 与 CI 日志，不算秘密）。
2. 确认没有 `test*` 账号：`--mode=system` 与 `--mode=test` 的区别就在这，**生产只允许 system**。
3. 打开 `/health` 与 `/ready`，确认 `postgres` 与 `redis` 都是 `ok`。

## 3. 常规发版

```bash
export IMAGE_TAG=$(git rev-parse --short HEAD)

# 1) 备份（回滚的唯一保险）
./scripts/backup-db.sh

# 2) 构建
docker compose build

# 3) 迁移：先于应用发布，且必须向后兼容
docker compose run --rm api migrate

# 4) 更新
docker compose up -d

# 5) 冒烟
curl -fsS https://api.example.com/ready
```

**迁移必须向后兼容**：一次发版内不能既删列又改代码。正确做法是分两次——先加列并双写，下一次发版再删旧列。否则回滚时旧代码会撞上已经不存在的列。

## 4. 回滚

| 层 | 动作 |
| --- | --- |
| 应用 | `export IMAGE_TAG=<上一个 tag>; docker compose up -d` |
| 迁移 | `docker compose run --rm api migrate downgrade -1`（**前提是 downgrade 已在预发验证过**） |
| 数据 | `RESTORE_DB=vctn ./scripts/restore-db.sh backups/<file>.dump` |

顺序：**先回滚应用，再回滚迁移，最后才考虑恢复数据**。数据恢复是最后手段，会丢掉备份点之后的所有写入。

## 5. 故障处置

| 症状 | 先看 | 处理 |
| --- | --- | --- |
| 前端打开是白屏，控制台一堆 404 | `curl -I https://ops.example.com/api/v1/...` | 99% 是 `/api/` 没反代。前端 `apiBaseUrl` 是相对路径，没有代理就全白屏且不报错 |
| 登录 401 但密码正确 | 应用日志 `invalid host header`；浏览器 Network 的 `Origin` | `ALLOWED_HOSTS` 缺该域名，或 `CORS_ORIGINS` 没列该来源 |
| 容器起不来，日志是 `ValueError` | `docker compose logs api` | 配置启动自检在拦。`production` 必须有 `ALLOWED_HOSTS`、`CORS_ORIGINS`、`AUTH_JWT_SECRET`，且 CORS 方法与头不能是 `*` |
| 502 Bad Gateway | `docker compose ps` | API 未通过健康检查。看 `docker compose logs api` 的启动异常 |
| 偶发 5 秒超时、请求排队 | 日志里 `QueuePool limit` | 连接池耗尽。核对 `replicas × (DB_POOL_SIZE + DB_MAX_OVERFLOW) ≤ 0.7 × max_connections` |
| Redis 挂了但业务还能用 | — | 这是设计：限流在 Redis 故障时 fail-open。会话与分布式锁会失效，需要重新登录，**尽快恢复 Redis** |
| 磁盘告警 | `docker system df`、`du -sh /var/lib/docker/containers` | 容器日志已限制 20m×7；先 `docker compose logs --tail` 定位，再清 |
| 主键冲突 / 数据串了 | — | **多实例 `SNOWFLAKE_NODE_ID` 重复**。每个副本必须唯一 |

## 6. 备份与演练

```bash
# 每日（crontab）
0 3 * * * cd /srv/vctn && PGPASSWORD=... ./scripts/backup-db.sh >> /var/log/vctn-backup.log 2>&1
```

**每季度必须做一次恢复演练**，在临时库上：

```bash
createdb vctn_restore_drill
RESTORE_DB=vctn_restore_drill ./scripts/restore-db.sh backups/<file>.dump
docker compose run --rm api migrate     # 迁移要能跑通
# 抽查几张核心表行数，然后 dropdb
```

没演练过的备份不算备份。

## 7. 日常维护

| 任务 | 命令 / 频率 |
| --- | --- |
| 数据保留清理 | `docker compose run --rm api clean --dry-run`（先看影响），确认后 `... api clean`。建议每日 |
| 日志归档 | 容器日志已轮转；应用侧日志见 `LOG_RETENTION_*_DAYS` |
| 证书续期 | HTTPS 模板已放行 `/.well-known/acme-challenge/` |
| 容量核对 | 每次扩副本后重算连接池与 `SNOWFLAKE_NODE_ID` |
| 密钥轮换 | `AUTH_JWT_SECRET` 轮换会让所有 token 失效，安排在业务低峰 |

## 8. 变更红线

- 生产禁止 `APP_DEBUG=true`（配置自检会拒绝启动）。
- 生产禁止启用 `/docs`（`DOCS_ENABLED` 默认在生产关闭）。
- 禁止把 `.env`、证书、备份提交进仓库（`.gitignore` 已覆盖，不要绕过）。
- 禁止同一 `SNOWFLAKE_NODE_ID` 跑两个副本。
- 禁止在生产执行 `seed --mode=test`。
