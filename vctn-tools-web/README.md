# vctn-tools-web

VCTN Tools 平台前端。

## 工程边界

- Tools 前端与管理平台前端是两个完全独立的工程，不互相 import。
- Tools 前端只访问同一个 FastAPI 后端 `vctn-api`。
- Tools 使用 `biz_user`，不处理 `sys_user`，不复制 Admin 的 RBAC。
- 前端隐藏不可访问的工具只是 UX，后端仍必须再次校验。

## 技术栈

Vue 3 + TypeScript + Vite + Vue Router + Pinia + Element Plus + Axios

## Phase 0 范围

工程初始化 + `ToolRegistry` / `ToolRuntime` 基础接口。

- 已冻结并落地的基础设施：ToolRegistry、ToolRuntime、component_key、FRONTEND/BACKEND/ASYNC 执行模式。
- 未冻结：最终 Tool API DTO、具体工具。因此本阶段**不注册任何具体工具**，也没有占位实现。

## 本地运行

```bash
npm install
npm run dev          # http://localhost:5174
npm run type-check
npm run build
npm test
```
