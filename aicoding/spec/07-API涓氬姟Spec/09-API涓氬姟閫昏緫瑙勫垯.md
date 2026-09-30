# 09 API → 业务逻辑统一规则

## 9.1 用户创建

```text
Controller
  ↓
UserService.create
  ↓
AuthorizationService.check_create_user
  ↓
DepartmentScopeService.validate
  ↓
RoleGrantService.validate_assignable
  ↓
PasswordService.hash
  ↓
transaction:
  sys_user
  sys_user_role
  Audit
  Outbox
```

## 9.2 权限判断

所有后台写操作：
```text
load target
→ check manageable scope
→ check action permission
→ check field permission
→ execute
```

不得：
```python
if current_user.is_super_admin:
    ...
```
作为散落式业务权限实现。

## 9.3 Audit FAILURE

以下任一情况：
- PermissionDenied
- data scope 越权
- role escalation
- department escalation
- force logout protected user
- invalid administrative operation

必须写 Security/Audit FAILURE，并带 trace_id/request_id。

## 9.4 Tool execution

```text
resolve subject
→ RiskService
→ ToolService.get_active_version
→ AccessPolicyService
→ QuotaService
→ RateLimitService
→ ConcurrencyService
→ ToolRuntime
→ UsageService
→ BehaviorAnalytics
→ Outbox
```

## 9.5 Points / Growth

禁止：
```text
ToolService → UPDATE biz_user_point_account
BlogService → UPDATE biz_user_growth_account
```

必须：
```text
ToolService
→ Outbox TOOL_EXECUTION_SUCCESS
→ Growth/Point consumer
→ account transaction
```

## 9.6 Blog publication

```text
load author
→ verify author approved
→ verify article belongs to author
→ validate article state
→ transaction:
   article status
   publication timestamp
   audit/event
→ Outbox ARTICLE_PUBLISHED
```

## 9.7 Analytics

埋点接口必须：
- 批量接收
- 事件白名单
- payload size limit
- sensitive-field filter
- event_id idempotency
- async aggregate

## 9.8 Export

```text
POST export
→ validate permission/filter
→ create export_job
→ enqueue ARQ job
→ return job_id
```

HTTP 请求不得执行大查询后同步生成大文件。

## 9.9 Concurrency

必须根据业务选择：
- unique constraint
- atomic UPDATE
- SELECT FOR UPDATE
- optimistic lock
- Redis Lua
- idempotency

不能通过应用层“先查再写”假设不存在并发。
