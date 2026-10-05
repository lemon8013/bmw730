# 13 未冻结项与 BLOCKER

以下项目在正式编码前必须由项目负责人冻结；AI Agent 不得自行决定：

1. DD-05 Role Inheritance SQL 具体实现
2. DD-07 CUSTOM Data Scope 存储结构
3. DD-08 Log Partitioning
4. DD-12 Error Code 完整目录
5. DD-13 Pagination 具体字段/语义
6. DD-14 Snowflake 位布局/worker 配置
7. DD-16 既有冻结项细节
8. MFA V1 provider 与完整流程
9. Access/Refresh Token TTL
10. Redis key/TTL 最终规范
11. Permission version/cache strategy
12. Feature Flag CONDITION grammar
13. Tool quota/rate/concurrency exact thresholds
14. Quota failure rollback/billing semantics
15. Point expiry
16. Level threshold / exact point-growth values
17. Task/achievement exact reward values
18. Blog article review/publish exact state machine
19. Analytics raw event retention
20. Export max range / max rows / file format
21. File storage provider
22. Notification provider
23. Search advanced grammar
24. Rate-limit exact values
25. Idempotency TTL
26. Secret manager
27. Log partitioning

规则：
`未冻结 → BLOCKER → 停止受影响接口实现`

禁止：
`未冻结 → AI 猜测 → 写死代码`
