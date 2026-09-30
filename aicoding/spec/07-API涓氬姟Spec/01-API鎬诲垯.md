# 01 API 总则

## 1.1 统一响应

成功：
```json
{"code":0,"message":"success","data":{}}
```

失败：
```json
{"code":403001,"message":"permission denied","data":null}
```

分页统一使用当前冻结规范；若当前工程尚未冻结具体字段，Agent 必须停止于 API-CONTRACT-BLOCKER，不得自行发明。

## 1.2 Header

- Authorization: Bearer <access-token>
- X-Trace-ID
- X-Request-ID
- Idempotency-Key：仅用于标记为幂等写操作的接口。

## 1.3 Controller 规则

Controller 只负责：
- 参数解析/校验
- 身份提取
- 调用 Service
- 返回 DTO
- 统一异常转换

Controller 不允许：
- 直接操作数据库
- 自己判断角色
- 自己扣积分
- 自己写统计聚合
- 自己发送通知
- 自己提交事务

## 1.4 Service 规则

Service 负责：
- 业务规则
- 权限调用
- 数据范围
- 事务
- 幂等
- 并发控制
- Domain Event
- Outbox
- 调用 Repository

## 1.5 Repository

Repository 只负责数据访问：
- select
- insert
- update
- delete/soft delete
- aggregate query

Repository 禁止 commit/rollback。

## 1.6 事件

典型：
`TOOL_EXECUTION_SUCCESS`
`TOOL_EXECUTION_FAILURE`
`USER_REGISTER`
`USER_LOGIN`
`ARTICLE_PUBLISHED`
`ARTICLE_LIKED`
`POINT_EARNED`
`USER_LEVEL_UP`

业务模块不得直接跨模块修改其他模块的账户表。

## 1.7 敏感数据

禁止进入日志、埋点、Audit before/after、异常 message：
- password
- MFA secret
- Authorization
- Cookie
- API key
- 完整 JWT
- 原始工具输入
- 上传文件内容
- 原始 SQL
