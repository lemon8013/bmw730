# 08-API 规范

## 1. Base URL

```text
/api/v1/admin
```

## 2. Response

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": 403001,
  "message": "permission denied",
  "data": null
}
```

BIGINT ID 在 JSON 中统一返回字符串。

## 3. Auth

```text
POST /auth/login
POST /auth/mfa/verify
POST /auth/refresh
POST /auth/logout
GET  /auth/me
GET  /auth/permissions
GET  /auth/mfa
POST /auth/mfa/setup
POST /auth/mfa/enable
POST /auth/mfa/disable
```

## 4. Users

```text
GET  /users
POST /users
GET  /users/{id}
PUT  /users/{id}
POST /users/{id}/disable
POST /users/{id}/enable
POST /users/{id}/reset-password
GET  /users/{id}/sessions
POST /users/{id}/sessions/revoke-all
```

## 5. Sessions

```text
GET  /sessions
POST /sessions/{id}/revoke
```

## 6. Departments

```text
GET  /departments/tree
POST /departments
PUT  /departments/{id}
POST /departments/{id}/disable
```

## 7. Roles

```text
GET  /roles
POST /roles
PUT  /roles/{id}
POST /roles/{id}/delete
GET  /roles/{id}/permissions
PUT  /roles/{id}/permissions/pages
PUT  /roles/{id}/permissions/menus
PUT  /roles/{id}/permissions/buttons
PUT  /roles/{id}/permissions/apis
PUT  /roles/{id}/permissions/fields
GET  /roles/{id}/data-scope
PUT  /roles/{id}/data-scope
```

## 8. Audit / Trace

```text
GET /audit/logs
GET /audit/logs/{id}
GET /traces
GET /traces/{traceId}
```

## 9. API 要求

- 所有受保护接口必须经过认证和授权。
- API 权限必须在后端校验。
- 参数校验使用 Pydantic。
- 统一异常处理。
- 统一分页格式。
- 统一排序与过滤规则。
- 敏感字段响应脱敏。
- 幂等接口明确幂等策略。
