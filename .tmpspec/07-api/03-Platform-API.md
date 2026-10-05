# 03 Platform API

Base: `/api/v1`

## Auth

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| POST | /auth/register | Public | 创建 biz_user、身份标识、profile；初始化成长/积分账户；写 USER_REGISTER event |
| POST | /auth/login | Public | 校验 login identity；创建 business session；写 USER_LOGIN |
| POST | /auth/refresh | Auth | 校验并轮换 refresh token |
| POST | /auth/logout | Auth | 撤销当前 session |
| GET | /auth/me | Auth | 返回当前业务用户 |
| POST | /auth/change-password | Auth | 密码策略/历史检查 |
| POST | /auth/send-verification | Public/Auth | 创建验证码请求，执行风控和频控 |
| POST | /auth/verify | Public/Auth | 校验验证码并完成对应验证动作 |

## User

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /users/me | Auth | 当前用户 profile |
| PUT | /users/me | Auth | 更新允许修改的 profile 字段 |
| GET | /users/me/sessions | Auth | 当前用户 sessions |
| POST | /users/me/sessions/{id}/revoke | Auth | 仅能撤销自己的 session |
| GET | /users/me/level | Auth | 当前等级 |
| GET | /users/me/growth | Auth | 成长值账户 |
| GET | /users/me/points | Auth | 积分余额/流水摘要 |
| GET | /users/me/cosmetics | Auth | 外观资产 |
| PUT | /users/me/equipment | Auth | 装备外观；校验 inventory |
| GET | /users/me/tasks | Auth | 当前任务 |
| GET | /users/me/achievements | Auth | 当前成就 |

## Levels / Growth / Points

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /levels | Public | 可公开等级信息 |
| GET | /levels/me | Auth | 当前等级和进度 |
| GET | /growth/me | Auth | growth account |
| GET | /growth/me/transactions | Auth | growth 流水 |
| GET | /points/me | Auth | point account |
| GET | /points/me/transactions | Auth | point 流水 |
| GET | /point-rules/public | Public | 当前对用户公开的规则 |
| GET | /cosmetics | Public/Auth | 可展示的外观 |
| GET | /cosmetics/me | Auth | 已拥有外观 |
| PUT | /cosmetics/me/equipment | Auth | 装备 |
| GET | /tasks | Auth | 可参与任务 |
| POST | /tasks/{id}/claim | Auth | 领取任务，幂等 |
| GET | /tasks/me | Auth | 我的任务 |
| GET | /achievements | Public/Auth | 成就列表 |
| GET | /achievements/me | Auth | 我的成就 |
