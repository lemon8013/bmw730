# 18 Trace 关联需求

复用既有：
- X-Trace-ID
- X-Request-ID

关联链路：

```text
Request
 -> API metric
 -> Access/Application Log
 -> Event
 -> Alert
 -> Audit（如有操作）
```

支持从：
- API
- Log
- Alert
- Job
- Event

跳转到 Trace 上下文。

不得要求重新建设另一套 Trace ID。
