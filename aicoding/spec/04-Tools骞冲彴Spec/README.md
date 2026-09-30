# VCTN 工具平台完整 Markdown Spec V1.0

本规格供 AI Coding Agent 按 **Spec → Agent → Verification** 直接实施。

## 文档
- 00-需求冻结.md
- 01-产品总体需求.md
- 02-工具管理后台.md
- 03-工具前台.md
- 04-工具插件与执行架构.md
- 05-访问策略与游客额度.md
- 06-使用统计与热门排序.md
- 07-数据模型与数据库设计.md
- 08-API规范.md
- 09-前端工程规范.md
- 10-后端工程规范.md
- 11-安全与隐私规范.md
- 12-开发阶段与验收.md
- 13-测试规范.md
- 14-完整性检查.md

## 总原则
1. 管理后台继续作为统一管理入口。
2. 工具网站使用独立二级域名，例如 `tools.example.com`。
3. 前端 Vue 3 + TypeScript + Vite。
4. 后端使用现有 FastAPI。
5. 工具执行 FRONTEND / BACKEND / ASYNC。
6. 工具开放、额度、限流、统计、热门统一平台化。
7. 统计不上传工具敏感输入。
8. 不增加 `tenant_id`。
9. BIGINT + Snowflake；JSON 中 BIGINT ID 使用字符串。
10. 未冻结的技术决策不得擅自发明；真实阻塞必须停止并报告。
