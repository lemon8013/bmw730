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
