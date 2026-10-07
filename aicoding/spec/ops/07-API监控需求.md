# 07 API 监控需求

## 指标
- Request Count
- RPS/QPS
- Average Response Time
- P50/P90/P95/P99
- 2xx/3xx/4xx/5xx
- Error Rate
- Slow API
- Trace ID 关联

## 维度
method、path、status_code、service、environment、time window。

## 安全
不得在监控指标中保存：
- Authorization
- Cookie 中敏感信息
- Password
- MFA Secret
- API Key
- JWT 原文

API 路径参数中的敏感值必须按规则脱敏。
