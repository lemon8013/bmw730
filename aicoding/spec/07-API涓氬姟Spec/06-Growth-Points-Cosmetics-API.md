# 06 Growth / Points / Cosmetics API

## Admin configuration

| Method | Path | 权限 | 业务逻辑 |
|---|---|---|---|
| GET | /admin/levels | LEVEL_CONFIG_VIEW | 查询等级 |
| POST | /admin/levels | LEVEL_CONFIG_EDIT | 创建等级 |
| PUT | /admin/levels/{id} | LEVEL_CONFIG_EDIT | 更新阈值/展示信息 |
| DELETE | /admin/levels/{id} | LEVEL_CONFIG_EDIT | 删除前检查用户引用 |
| GET | /admin/growth-rules | GROWTH_RULE_VIEW | 查询 |
| POST | /admin/growth-rules | GROWTH_RULE_EDIT | 创建 |
| PUT | /admin/growth-rules/{id} | GROWTH_RULE_EDIT | 更新 |
| GET | /admin/point-rules | POINT_RULE_VIEW | 查询 |
| POST | /admin/point-rules | POINT_RULE_EDIT | 创建 |
| PUT | /admin/point-rules/{id} | POINT_RULE_EDIT | 更新 |
| GET | /admin/cosmetics | COSMETIC_VIEW | 查询 |
| POST | /admin/cosmetics | COSMETIC_EDIT | 创建 |
| PUT | /admin/cosmetics/{id} | COSMETIC_EDIT | 更新 |
| DELETE | /admin/cosmetics/{id} | COSMETIC_EDIT | 删除 |
| POST | /admin/users/{id}/growth-adjustments | USER_GROWTH_ADJUST | 管理员调整成长值；必须 Audit |
| POST | /admin/users/{id}/point-adjustments | USER_POINT_ADJUST | 管理员调整积分；必须 Audit |

## Internal business services

这些是 Service Contract，不暴露 HTTP：
- `GrowthService.apply_event(event)`
- `PointService.apply_event(event)`
- `LevelService.recalculate(user_id)`
- `CosmeticService.grant(user_id, cosmetic_id)`
- `TaskService.consume_event(event)`
- `AchievementService.consume_event(event)`

## 核心逻辑

`TOOL_EXECUTION_SUCCESS` 等业务事件进入 Outbox。

Growth/Point consumer：
1. 读取 event_id/idempotency_key。
2. 检查是否已经处理。
3. 查询匹配规则。
4. 计算 reward。
5. 锁定账户行。
6. 写 transaction。
7. 更新 account balance/total growth。
8. 写处理幂等记录。
9. 若跨越等级阈值，写 level_history + USER_LEVEL_UP event。

不得由 ToolService 直接修改 point/growth account。
