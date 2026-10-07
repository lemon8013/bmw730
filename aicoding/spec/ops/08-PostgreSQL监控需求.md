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
