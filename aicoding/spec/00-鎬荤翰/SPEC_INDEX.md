# VCTN 完整开发规格总索引 V1.0

## 1. 目标

本包用于指导 VCTN 项目后续 AI Coding / 人工开发，覆盖：

- 管理平台后端
- 管理平台前端
- 完整统一数据库
- Tools 产品后端/产品能力
- Tools 独立前端
- AI Coding Agent 工作协议与 Verification

数据库设计已经完成，本版本以 `03-完整数据库设计` 中的 V3.1 为当前数据库基线，不重新设计数据库。

## 2. 系统总体架构

```text
                         ┌──────────────────────┐
                         │     FastAPI Backend   │
                         │      api.xxx.com      │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
       ┌────────────────┐  ┌────────────────┐  ┌───────────────┐
       │ Admin Web      │  │ Tools Web      │  │ Blog Web      │
       │ admin.xxx.com  │  │ tools.xxx.com  │  │ future        │
       └────────────────┘  └────────────────┘  └───────────────┘
```

### Admin Web

现有 `frontend` 管理平台继续独立存在。

负责：

- 后台管理员
- 部门
- 角色
- Page/Menu/Button/API/Field/Data Scope
- 登录认证
- MFA
- Session
- 字典/系统参数
- 日志/审计/Trace
- Tools 后台管理
- 后续 Blog 后台管理

### Tools Web

独立项目、独立域名、独立构建、独立部署。

负责：

- 工具首页
- 分类
- 搜索
- Tool 工作台
- Tool Registry / Runtime
- 游客/业务用户使用
- 使用统计展示
- 用户中心
- 等级/成长/积分/外观展示

## 3. 前端隔离原则

```text
Admin Web                    Tools Web
─────────                    ─────────
Router                       Router
Pinia                        Pinia
Layout                       Layout
Views                        Views
Components                   Components
Business Logic               Business Logic
Build                        Build
Deploy                       Deploy
```

两者不得互相 import，不通过 iframe 拼接，不依赖对方 build 产物。

共享的是后端 API Contract，而不是前端源码。

## 4. 数据库基线

当前完整数据库设计：

```text
03-完整数据库设计/
```

覆盖：

1. 系统管理域
2. 统一业务用户域
3. 用户成长中心
4. Tools 工具域
5. Blog 博客域
6. 日志审计与字典域
7. 表关系与索引规范
8. PostgreSQL DDL 基线
9. 数据库完整性检查

其中核心身份明确区分：

```text
sys_user  = 后台管理用户
biz_user  = Blog / Tools 等业务用户
```

系统不增加 `tenant_id`，当前为单组织/单公司模型。

## 5. 文档优先级

### 业务规则

1. `01-管理平台后端Spec/00-需求冻结确认表.md`
2. 其他管理平台后端 Spec
3. Tools 冻结文档
4. Tools Web Spec
5. Agent 协议
6. 当前代码

### 数据库

数据库实际表结构、字段、关系、DDL 以：

```text
03-完整数据库设计/
```

中的 V3.1 为基线。

### 前端

管理平台：

```text
02-管理平台前端Spec/
```

Tools：

```text
05-Tools独立前端Spec/
```

## 6. 已明确的重要边界

- Admin 用户不是 Tools/Blog 业务用户。
- Tools 不实现 Admin RBAC。
- Tools 使用 `biz_user`。
- Blog 后续同样使用 `biz_user`。
- Tools 与 Admin 不共用前端工程源码。
- 游客额度主要依据 `anonymous_id`，IP 用于防刷/风险/限流，不作为唯一游客身份。
- Tool 执行采用 Registry + Runtime。
- 前端不能通过硬编码替代后端权限、额度或等级规则。
- 本地可完成的 Tool 默认优先本地执行，避免上传用户原始数据。

## 7. 当前待冻结项

以下内容不能由 Agent 自行发明：

- MFA V1 Provider
- JWT/Session 精确生命周期
- Redis Key/TTL 最终方案
- 权限缓存版本方案
- Role Inheritance 最终 SQL 方案
- CUSTOM Data Scope 存储方案
- 日志分区方案
- UI 组件库
- Tool API 最终 DTO
- 热门排序 score 公式
- 积分过期
- 等级具体数值
- 积分奖励具体数值
- 积分商城
- 活动/邀请

遇到这些问题必须进入 BLOCKER/待冻结流程，不得静默决策。

## 8. 开发流程

```text
SPEC
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
VERIFY
 ↓
FIX
 ↓
VERIFY AGAIN
 ↓
PASS
```

禁止跳过 Verification 直接进入下一阶段。
