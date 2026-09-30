# 07 Analytics API

## Event ingest

`POST /api/v1/analytics/events`

请求核心结构：
```json
{
  "events": [
    {
      "event_id": "string",
      "event_code": "TOOL_EXECUTE",
      "occurred_at": "UTC timestamp",
      "page_code": "tool.json-format",
      "resource_type": "TOOL",
      "resource_id": "string",
      "properties": {
        "tool_code": "json-format",
        "success": true,
        "duration_ms": 18
      }
    }
  ]
}
```

服务端不得信任 client 的：
- user_id
- anonymous_id_hash
- session ownership
- operator/admin identity

服务端自行补全 identity/context。

## Event service

`AnalyticsService.ingest(events)`
1. 验证 event_code。
2. 限制 payload 大小。
3. 删除/拒绝敏感字段。
4. 服务端补全 anonymous/user/session/page/app/device。
5. event_id 幂等。
6. 批量 insert。
7. 不同步执行大聚合。
8. 异步聚合到 daily/funnel/retention。

## Anonymous identity merge

`POST /api/v1/analytics/identity/merge`

通常由登录/注册流程内部调用，不建议开放为任意公共 API。

逻辑：
`anonymous_id_hash → biz_user_id`
必须校验当前 session 与 anonymous identity 的归属。

## Admin Analytics

| Method | Path | 权限 |
|---|---|---|
| GET | /admin/analytics/overview | ANALYTICS_DASHBOARD_VIEW |
| GET | /admin/analytics/users | ANALYTICS_VIEW |
| GET | /admin/analytics/tools | ANALYTICS_VIEW |
| GET | /admin/analytics/pages | ANALYTICS_VIEW |
| GET | /admin/analytics/events | ANALYTICS_EVENT_VIEW |
| GET | /admin/analytics/funnels | ANALYTICS_VIEW |
| GET | /admin/analytics/trends | ANALYTICS_VIEW |
| GET | /admin/analytics/search | ANALYTICS_VIEW |
| GET | /admin/analytics/retention | ANALYTICS_VIEW |
| POST | /admin/analytics/export | ANALYTICS_EXPORT |

行为埋点与 Tool Usage 必须分开存储：
`TOOL_EXECUTE → tool_usage_event + behavior_event`。
