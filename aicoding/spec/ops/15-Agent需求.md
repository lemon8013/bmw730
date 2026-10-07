# 15 Agent 需求

Agent 负责：
- CPU
- Memory
- Disk
- Network
- Process/host 基础信息
- Heartbeat

Server 负责：
- Agent 注册
- Agent 身份校验
- Agent 状态
- 最后心跳
- 版本
- 升级状态
- 禁用/启用

Agent 状态候选：
ONLINE、OFFLINE、UPGRADING、UNKNOWN。

通信协议目前不冻结。候选：
HTTPS REST、gRPC、WebSocket、MQTT 等。

禁止 Agent 自带高风险远程执行能力。
