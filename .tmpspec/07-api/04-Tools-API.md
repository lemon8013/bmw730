# 04 Tools API

## 用户/游客

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools | Public | 按 category/status/access 返回可见工具 |
| GET | /tools/{id} | Public | 工具详情 |
| GET | /tools/by-slug/{slug} | Public | slug 查询 |
| GET | /tool-categories | Public | 分类 |
| GET | /tools/popular | Public | 热门 |
| GET | /tools/recent | Auth | 当前用户最近使用 |
| GET | /tools/{id}/access | Public/Auth | 服务端解析 guest/user/user level，返回 allowed/quota/rate 信息 |
| POST | /tools/{id}/usage | Public/Auth | 服务端识别 subject，检查 access/quota/rate/concurrency，执行或记录使用 |

## Tool usage 业务逻辑

1. 解析 authenticated biz_user 或 anonymous_id。
2. anonymous_id 必须不可预测；服务端存 hash。
3. RiskService 检查风险。
4. AccessPolicyService 判断工具是否 ACTIVE。
5. Permission/level policy 判断是否允许。
6. Redis Lua 原子扣 quota / rate。
7. FRONTEND 工具：前端执行后仅上报 usage event，不上传输入内容。
8. BACKEND：ToolRuntime 调 Provider。
9. ASYNC：创建 job，返回 job_id。
10. 记录 tool_usage_event。
11. 写 TOOL_EXECUTE_SUCCESS/FAILURE 行为事件。
12. 根据业务事件进入 Outbox，Growth/Points 异步处理。
13. 失败必须正确回滚 quota 或按冻结的计费规则处理；该规则未冻结时标记 BLOCKER。

## Async Tool Jobs

| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools/jobs/{job_id} | Auth/Public按任务策略 | 仅返回当前 subject 可见任务 |
| POST | /tools/jobs/{job_id}/cancel | Auth | 仅取消自己的可取消任务 |

## Tool search
| Method | Path | Auth | 业务逻辑 |
|---|---|---|---|
| GET | /tools/search | Public | SearchService 查询 tool/category |
