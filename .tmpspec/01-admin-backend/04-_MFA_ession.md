# 04-认证、MFA 与 Session

## 1. 登录流程

```text
username/password
 ↓
用户查询
 ↓
状态检查
 ↓
锁定检查
 ↓
密码校验
 ↓
MFA 检查
 ↓
创建 Session
 ↓
签发 Token
 ↓
Security/Audit Log
 ↓
Response
```

## 2. 密码策略

- 最少 12 位
- 大写字母
- 小写字母
- 数字
- 特殊字符
- 最近 5 次不能重复
- 90 天必须修改
- 连续 5 次失败锁定 30 分钟
- 管理员重置后首次登录必须修改

推荐 Argon2id。

## 3. MFA

架构：

```text
MfaProvider
├── TOTP
├── Email
├── SMS
├── WebAuthn/Passkey
└── Future Provider
```

MFA 强制支持：

- 角色级
- 用户级

优先级：

```text
用户级 > 角色级 > 系统默认
```

Secret 加密存储，禁止日志记录。

## 4. Session

Session 至少包括：

- id
- user_id
- token_id/jti
- refresh_token_hash
- login_at
- last_active_at
- ip
- user_agent
- device_info
- expires_at
- revoked_at
- revoked_reason
- created_at
- updated_at

支持：

- 在线状态
- 单 Session 撤销
- 全 Session 撤销
- 强制下线

## 5. 超级管理员

超级管理员 Session 不允许被其他管理员撤销。

## 6. Token

JWT 包含 `session_id`。

Refresh Token 不保存明文，只保存哈希。

具体 Access/Refresh 生命周期在技术设计中统一配置。
