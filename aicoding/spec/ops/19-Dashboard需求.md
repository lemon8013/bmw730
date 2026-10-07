# 19 Dashboard 需求

默认 Dashboard：
- System Overview
- Host
- Service
- API
- PostgreSQL
- Redis
- Tools
- Alerts

Widget 类型候选：
- Stat
- Line
- Area
- Bar
- Table
- Gauge
- Heatmap
- TopN
- Timeline
- Dependency Graph

Dashboard 支持：
- 查询时间范围
- 自动刷新
- Widget 排序
- 权限控制

自定义 Dashboard 的编辑能力属于 V1 范围，但 Widget 类型和布局模型需在 DB/API 设计阶段冻结。
