# 后台管理平台 V1.0 需求文档包

## 技术基线

- 后端：Python + FastAPI
- 数据库：PostgreSQL
- ORM：SQLAlchemy
- 数据库迁移：Alembic
- 缓存/会话辅助：Redis
- 核心业务 ID：BIGINT + Snowflake
- API JSON 中 BIGINT ID：字符串
- 单组织/单公司模型，不支持多租户
- 权限：RBAC + Page/Menu/Button/API/Field/Data Scope
- 认证：JWT + Session
- MFA：可扩展 Provider 架构
- 日志：Access / Security / Operation / Audit / Application
- Trace：X-Trace-ID + X-Request-ID

## 文档目录

1. 00-需求冻结确认表.md
2. 01-总体需求.md
3. 02-组织与用户.md
4. 03-角色与权限.md
5. 04-认证MFA与Session.md
6. 05-字典与系统参数.md
7. 06-日志审计与Trace.md
8. 07-数据库设计.md
9. 08-API规范.md
10. 09-前端动态权限.md
11. 10-安全设计.md
12. 11-缓存并发幂等.md
13. 12-测试与验收.md
14. 13-运维部署.md
15. 14-AI Coding Agent开发规范.md
16. 15-需求决策记录.md
17. 16-完整性检查.md

> 需求冻结以 `00-需求冻结确认表.md` 为最高优先级。后续技术设计不得擅自改变已冻结业务规则。
