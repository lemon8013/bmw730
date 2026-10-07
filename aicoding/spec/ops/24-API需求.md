# 24 API 需求

Base：

`/api/v1/ops`

## Dashboard
GET `/overview`

## Hosts
GET `/hosts`
GET `/hosts/{id}`
POST `/hosts`
PUT `/hosts/{id}`
DELETE `/hosts/{id}`

## Services
GET `/services`
GET `/services/{id}`
POST `/services`
PUT `/services/{id}`
DELETE `/services/{id}`

## APIs
GET `/apis`
GET `/apis/{id}`
GET `/apis/{id}/metrics`

## Metrics
GET `/metrics`
GET `/metrics/series`

## Logs
GET `/logs`
GET `/logs/{id}`

## Events
GET `/events`
GET `/events/{id}`

## Alerts
GET `/alerts`
GET `/alerts/{id}`
POST `/alerts/{id}/ack`
POST `/alerts/{id}/silence`
POST `/alerts/{id}/resolve`（仅系统/受控流程，不允许任意伪造）

## Alert Rules
GET `/alert-rules`
POST `/alert-rules`
PUT `/alert-rules/{id}`
DELETE `/alert-rules/{id}`

## Notifications
GET `/notifications`
GET `/notification-channels`
POST `/notification-channels`
PUT `/notification-channels/{id}`

## Agents
GET `/agents`
GET `/agents/{id}`
POST `/agents/{id}/enable`
POST `/agents/{id}/disable`

## Availability
GET `/availability`
POST `/availability`
PUT `/availability/{id}`
DELETE `/availability/{id}`

## Jobs
GET `/jobs`
GET `/jobs/{id}`
POST `/jobs/{id}/retry`
POST `/jobs/{id}/stop`

## Maintenance
GET `/maintenance`
POST `/maintenance`
PUT `/maintenance/{id}`
DELETE `/maintenance/{id}`

## Dashboards
GET `/dashboards`
GET `/dashboards/{id}`
POST `/dashboards`
PUT `/dashboards/{id}`
DELETE `/dashboards/{id}`

实际 DTO、状态码、分页结构、幂等策略必须与现有 API Spec 一致。
