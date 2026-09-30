# VCTN 完整 Spec + SQL V2.2

这是给 AI Coding Agent 使用的汇总开发包。

## 核心文件
- `VCTN-Complete-Spec-V2.2.md`：完整总 Spec
- `sql/vctn-enterprise-ddl-v2.0.sql`：完整 PostgreSQL DDL 基线

## 配套目录
- `spec/`：原始开发 Spec、前端 Spec、Tools Spec、数据库设计、API Business Spec、Agent/Verification 规则
- `sql/`：SQL 基线

## Agent 原则
1. 以 Spec/API/DDL 为准。
2. 未冻结项 = BLOCKER，不能自行决定。
3. 不新增第三方依赖。
4. 不增加 tenant_id。
5. BIGINT ID API JSON 使用 string。
6. Service 负责业务事务边界，Repository 不 commit。
7. Backend authorization 是最终权威。
## 项目根目录（冻结）

本项目唯一项目根目录：

```text
D:\project\bmw730
```

三个工程必须位于：

```text
D:\project\bmw730\
├── vctn-api\
├── vctn-admin-web\
└── vctn-tools-web\
```

禁止 AI Coding Agent 在其他路径创建项目、复制项目或重新选择项目根目录。

