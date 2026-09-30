# vctn-admin-web

VCTN 管理平台前端。

## 工程边界

- 管理平台前端与 Tools 前端是两个完全独立的工程。
- 两者不互相 import，不使用 iframe 拼接，不依赖对方的构建产物。
- 共享的是后端 API Contract，而不是前端源码。
- 两个前端都只访问同一个 FastAPI 后端 `vctn-api`。

## 技术栈

Vue 3 + TypeScript + Vite + Vue Router + Pinia + Element Plus + Axios

## Phase 0 范围

只包含工程初始化与基础设施：Vue / Router / Pinia / Element Plus 初始化、
Axios 基础实例（统一 envelope、X-Trace-ID、X-Request-ID、网络错误归一化）。

不包含登录页、用户页、角色页、权限页、部门页、菜单页、Dashboard 以及任何业务 API。

## 本地运行

```bash
npm install
npm run dev          # http://localhost:5173
npm run type-check
npm run build
npm test
```
