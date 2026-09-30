# VCTN API + Business Logic Specification v2.1

本包用于 AI Coding Agent 直接按 API Contract 实现业务逻辑。

原则：
1. API → Controller → Service → Repository → Domain/Event 的实现链路固定。
2. 不允许 Agent 根据接口名称自行猜业务规则。
3. 未冻结的规则必须标记 BLOCKER，不得自行决定。
4. Repository 不提交事务；Service 管理事务边界。
5. 权限以后端 AuthorizationService 为最终依据。
6. 跨模块副作用通过 Outbox / Domain Event。
7. BIGINT/Snowflake 在 JSON 中统一序列化为 string。
8. 所有时间使用 UTC。
9. API Base Path：`/api/v1`。
10. 本包只覆盖开发阶段；部署/运维暂不纳入。

目录：
- 01-API总则.md
- 02-Admin-API.md
- 03-Platform-API.md
- 04-Tools-API.md
- 05-Blog-API.md
- 06-Growth-Points-Cosmetics-API.md
- 07-Analytics-API.md
- 08-System-API.md
- 09-API业务逻辑规则.md
- 10-Controller-Service规范.md
- 11-权限矩阵.md
- 12-接口实现验收.md
- 13-未冻结项与BLOCKER.md
