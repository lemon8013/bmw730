# 08 API 规范

Base：`/api/v1`

统一响应：
`{"code":0,"message":"success","data":{}}`

ID JSON 为字符串。

## 前台
- GET `/tools`
- GET `/tools/{id}`
- GET `/tools/by-slug/{slug}`
- GET `/tool-categories`
- GET `/tools/popular`
- GET `/tools/recent`
- POST `/tools/{id}/usage`

列表支持分页、分类、关键词、状态由服务端按场景决定。

## 访问/额度
前台执行前可通过统一能力获取当前工具访问状态，例如：
`GET /tools/{id}/access`

返回：
- allowed
- subject_type
- daily_limit
- used_today
- remaining_today
- rate_limit

敏感内部信息不得返回。

## 管理端
- GET/POST `/admin/tools`
- GET/PUT `/admin/tools/{id}`
- POST `/admin/tools/{id}/publish`
- POST `/admin/tools/{id}/disable`
- GET/POST `/admin/tool-categories`
- GET/PUT/DELETE `/admin/tool-categories/{id}`
- GET/POST `/admin/tools/{id}/versions`
- GET/PUT `/admin/tools/{id}/access-policies`
- GET `/admin/tools/{id}/statistics`
- GET `/admin/tools/statistics/overview`
- GET `/admin/tools/popular`

具体请求/响应 DTO 必须在实现前按现有 API 规范补全。

## Usage API
必须服务端识别主体并执行额度检查，不能信任客户端传入 user_id、anonymous_id、used_count。

## 错误
沿用现有 error code 分段、分页和 trace/request ID 规范。
