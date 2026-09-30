# 14 开发阶段与 AI Coding Agent 执行规范

## 工作流

```text
Spec → Agent → Verification → Fix → Verification
```

## Phase 0

创建独立项目、Vue3、TS、Vite、Router、Pinia、环境配置、目录、README。

## Phase 1

DefaultLayout、Header、Footer、Loading、Empty、Error、404。

## Phase 2

首页、搜索、分类、热门、最近使用、Tool Card。

## Phase 3

ToolDefinition、Registry、Runtime、componentKey 白名单、lazy loading。

## Phase 4

完成 JSON Formatter 全链路：页面、Registry、Runtime、本地执行、错误、Usage、测试。

## Phase 5

批量完成 JSON Minify、Validate、Base64、UUID、Timestamp、URL、Diff。

## Phase 6

Login、Register、Logout、User state、Route Guard。

## Phase 7

Guest/User Access、Quota、Rate Limit、Usage。

## Phase 8

Profile、Level、Growth、Points、Cosmetic。

## Phase 9

测试、安全、性能、可访问性、部署。

## Agent 停止条件

遇到以下情况不得自行发明：

- API DTO 不一致
- Error Code 未冻结
- Auth Token 规则未冻结
- component_key 未定义
- Access API 未实现
- User API 不明确
- 业务规则冲突

必须报告 BLOCKER、影响、需要冻结的决策和不能安全继续的原因。

## 禁止

不得修改 Admin Web 来方便 Tools；不得把 Tools 放进 Admin Router；不得复制 Admin RBAC；不得硬编码等级/热门/额度规则；不得上传工具输入；不得任意动态 import；不得用大量 if/else。
