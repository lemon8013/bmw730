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
