# VCTN 完整开发规格包 V1.0

这是 VCTN 当前完整开发规格基线。

## 包含内容

- 管理平台后端完整需求/Spec
- 管理平台前端完整 Spec
- 统一完整数据库设计 V3.1 + PostgreSQL DDL
- Tools 产品/后端 Spec
- Tools 独立前端 Spec
- AI Coding Agent 协议
- Verification 工作流

## 最重要的架构决策

```text
Admin Web  ≠  Tools Web

admin.xxx.com  → 管理平台
 tools.xxx.com → Tool 平台
 api.xxx.com   → FastAPI
```

数据库统一，但前端应用隔离。

## 推荐使用方式

先让 Agent 阅读：

```text
00-总纲/SPEC_INDEX.md
00-总纲/03-Agent首轮提示词.md
00-总纲/AGENTS.md
```

然后按 Phase 开发和验证。
