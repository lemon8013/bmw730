# AI Coding Agent Rules

1. 先读 Spec，再写代码。
2. 先读 Dependency Index，再安装依赖。
3. 禁止安装未列出的第三方包。
4. 禁止用同类包替换冻结包。
5. 禁止增加 tenant_id。
6. 禁止把 Admin API 和 Platform API 拆成两个服务。
7. 禁止建立第二套 Business User。
8. 禁止 Repository 自己 commit。
9. Service Layer 是事务边界。
10. 权限必须通过 AuthorizationService。
11. PermissionDenied 必须记录 Security/Audit FAILURE。
12. Tools/Blog 不得直接修改积分/成长账户。
13. 跨模块副作用优先使用 Outbox。
14. BIGINT API 必须序列化为字符串。
15. 时间统一 UTC。
16. 不得记录密码、MFA Secret、Token、API Key、Cookie、Authorization、原始用户输入、上传文件内容。
17. 不得自行决定未冻结的 MFA Provider、Token TTL、Redis key/TTL、Role Inheritance SQL、CUSTOM Data Scope 存储、日志分区、积分规则等。
18. 遇到依赖、API、DB、权限、安全、Migration 冲突必须暂停。

Blocker：
- DEPENDENCY-BLOCKER
- API-CONTRACT-BLOCKER
- DB-SCHEMA-BLOCKER
- PERMISSION-BLOCKER
- SECURITY-BLOCKER
- MIGRATION-BLOCKER
- SPEC-CONFLICT
