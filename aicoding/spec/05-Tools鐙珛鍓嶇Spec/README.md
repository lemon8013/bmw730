# VCTN Tools Web 前端开发规格文档 V1.0

## 1. 定位

本规格用于直接指导 AI Coding Agent 开发独立的 VCTN Tools 前端项目。

- Admin Web：现有 `frontend`，继续负责管理平台。
- Tools Web：新建独立项目 `vctn-tools-web`。
- 两者独立源码、package.json、Vite、构建、部署。
- 不共享 Router、Pinia Store、Layout、View、业务组件。
- 通过统一 FastAPI API 通信。
- 数据库设计已经完成，本 Spec 不重新设计数据库。

## 2. 生产域名

- Admin：`https://admin.example.com`
- Tools：`https://tools.example.com`
- API：`https://api.example.com`

实际域名通过环境变量配置。

## 3. 技术基线

Vue 3 + TypeScript + Vite + Vue Router + Pinia。
UI 组件库暂不冻结，Agent 不得擅自做不可逆选择。
BIGINT ID 前端统一使用 `string`。
API 使用统一 envelope、Trace ID、Request ID。

## 4. Tools 产品范围

- 首页
- 分类
- 搜索
- Tool 工作台
- 热门工具
- 最近使用
- 游客额度
- 登录/注册
- 用户中心
- 等级/成长值/积分
- Avatar/Crown/Frame 等外观
- Tool Registry
- Tool Runtime
- Usage Reporter

## 5. 不属于 Tools Web

- 管理员登录
- Admin RBAC
- 部门/角色/权限管理
- Tool 后台配置、发布、统计管理页面

以上属于 Admin Web。

## 6. 核心原则

1. Admin 与 Tools 完全隔离。
2. 后端是权限和额度的最终权威。
3. Tool 采用 Registry + Runtime 插件化。
4. 不使用大量 `if/else` 判断 Tool。
5. 能本地处理的数据默认不上传。
6. 不记录密码、Token、API Key、JWT、Cookie、工具原始输入等敏感数据。
7. 等级、积分、成长规则由后端驱动，前端只展示。

## 7. 开发顺序

项目骨架 → Layout → 首页 → 分类/搜索 → Registry/Runtime → 第一批 Tool → 登录/注册 → 额度/统计 → 用户中心 → 等级成长积分外观 → 安全/性能/测试。

## 8. 完成标准

独立启动、独立 build、独立部署；不依赖 Admin；核心路由、Registry、Runtime、Usage、Quota、登录、用户中心均通过验证；TypeScript/Lint/Test/Build 通过。
