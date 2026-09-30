# VCTN SQL 基线

主 DDL：`vctn-enterprise-ddl-v2.0.sql`

说明：
- PostgreSQL
- BIGINT + 应用层 Snowflake ID
- UTC/TIMESTAMPTZ
- 无 tenant_id
- 包含 Admin、业务用户、成长积分、Tools、Blog、Analytics、Outbox、幂等、Job、Notification、File、Export、Risk、Log/Audit 等表。
- SQL 中明确列出的业务不变量仍需由 Service/Authorization 层保证。
