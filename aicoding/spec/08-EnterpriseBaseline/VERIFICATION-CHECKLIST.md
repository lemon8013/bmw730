# Verification Checklist

## Architecture
- [ ] 双前端独立
- [ ] 单 FastAPI 模块化单体
- [ ] 无 tenant_id
- [ ] sys_user 与 biz_user 分离

## Dependencies
- [ ] 依赖与清单一致
- [ ] lock 文件存在
- [ ] 无未批准第三方包
- [ ] 无重复 ORM/HTTP/Redis/UI/Task/Scheduler

## Database
- [ ] PostgreSQL DDL 可执行
- [ ] Alembic 基线一致
- [ ] Snowflake BIGINT
- [ ] FK/UNIQUE/CHECK 正确
- [ ] 软删除索引正确

## Security
- [ ] 密码策略
- [ ] 密码历史
- [ ] Session 撤销
- [ ] MFA Secret 保护
- [ ] RBAC
- [ ] Field Permission
- [ ] Data Scope
- [ ] 越权 Audit
- [ ] Rate Limit
- [ ] Idempotency

## Tools
- [ ] Registry
- [ ] Component Registry
- [ ] Runtime Mode
- [ ] Guest Anonymous ID
- [ ] Quota
- [ ] Usage Event
- [ ] Popularity

## Business User / Growth
- [ ] 注册登录
- [ ] Level
- [ ] Growth
- [ ] Points
- [ ] Cosmetics
- [ ] Tasks
- [ ] Achievements

## Blog
- [ ] Author Application
- [ ] Review
- [ ] Article
- [ ] Comment
- [ ] Like
- [ ] Favorite
- [ ] Follow
- [ ] View Count

## Analytics
- [ ] SDK
- [ ] Anonymous ID
- [ ] Identity Merge
- [ ] Batch Upload
- [ ] Privacy Filtering
- [ ] Daily Aggregation
- [ ] Funnel
- [ ] Retention

## Reliability
- [ ] Transaction Boundary
- [ ] Outbox
- [ ] Idempotency
- [ ] Concurrency
- [ ] Async Job
- [ ] Scheduler
- [ ] Notification
- [ ] Export Job

## Frontend
- [ ] Dynamic routes
- [ ] Dynamic menu
- [ ] Button permission
- [ ] Field permission
- [ ] OpenAPI generated types
- [ ] Unit
- [ ] E2E

## Deferred
- [ ] Deployment/Operations remain deferred
- [ ] No Docker/K8s/CI/CD/production monitoring added to current development scope
