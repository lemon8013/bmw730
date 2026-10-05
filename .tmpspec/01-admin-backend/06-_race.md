# 06-日志、审计与 Trace

## 1. 五类日志

| 类型 | 保存 |
|---|---:|
| Access Log | 30 天 |
| Security Log | 180 天 |
| Operation Log | 180 天 |
| Audit Log | 2 年 |
| Application Log | 30 天 |

## 2. Audit Log

至少包括：

- audit_log_id
- trace_id
- request_id
- operator_id
- operator_username
- action
- resource_type
- resource_id
- before_data
- after_data
- result
- error_code
- ip
- user_agent
- created_at

Audit Log 原则上追加写入。

## 3. Security Log

记录：

- 登录成功/失败
- 锁定
- MFA
- 密码修改/重置
- Session 撤销
- 强制下线
- 安全异常

## 4. Access Log

记录请求访问行为。

## 5. Operation Log

记录后台管理操作。

## 6. Trace

请求支持：

```text
X-Trace-ID
X-Request-ID
```

缺失时自动生成。

Trace 必须贯穿：

```text
Middleware
→ Controller
→ Service
→ Repository
→ Log
```

## 7. 脱敏

- 手机：138****1234
- 邮箱：abc***@example.com
- Token：前 6 位
- 密码：禁止
- MFA Secret：禁止

禁止将敏感字段放入 Exception Message。
