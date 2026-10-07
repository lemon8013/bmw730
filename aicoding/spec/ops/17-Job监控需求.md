# 17 Job 监控需求

监控现有：
- sys_job
- sys_job_definition

状态：
RUNNING、SUCCESS、FAILURE、TIMEOUT、CANCELLED 等。

统计：
- success rate
- failure rate
- avg/max duration
- repeated failures
- timeout
- long-running

支持受权限控制的 Retry/Stop 操作。

任何 Job 操作必须写入 Audit。
