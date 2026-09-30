# 10 Controller / Service / Repository 实现规范

目录建议：

```text
app/
  admin/
    users/
      router.py
      schemas.py
      service.py
      repository.py
      models.py
      permissions.py
    roles/
    permissions/
    ...
  platform/
    users/
    growth/
    points/
    tools/
    blog/
    analytics/
  shared/
    auth/
    authorization/
    database/
    redis/
    idempotency/
    events/
    outbox/
    jobs/
    exceptions/
    logging/
    tracing/
```

每个 HTTP API：
`router -> schema -> service -> repository`

跨模块：
`service -> domain event -> outbox -> consumer/service`

每个写 Service 必须明确：
- transaction boundary
- authorization check
- data scope
- idempotency
- concurrency
- audit
- event/outbox
- return DTO

每个接口必须存在：
- request schema
- response schema
- service method
- repository methods
- error mapping
- test case

禁止：
- router 直接 SQL
- repository commit
- Service 内部直接 import FastAPI Request 作为业务依赖
- 跨模块直接修改其他模块表
- 未注册工具 component_key
- 客户端传 user_id 决定权限
