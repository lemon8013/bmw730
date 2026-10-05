# VCTN Tools Web Spec Index V1.0

本套 Spec 以“Admin Web 与 Tools Web 完全独立”为核心架构。

| 文档 | 内容 |
|---|---|
| README.md | 总体说明 |
| 01-项目边界与总体架构.md | 项目隔离与部署架构 |
| 02-工程结构与技术规范.md | Vue/TS/Vite 工程规范 |
| 03-页面与路由规格.md | 页面与路由 |
| 04-UI与交互设计规范.md | UI/UX |
| 05-Tool插件与Runtime规范.md | Registry/Runtime |
| 06-API与状态管理规范.md | API/Pinia |
| 07-认证与业务用户规范.md | Guest/biz_user |
| 08-游客额度与使用统计.md | Quota/Usage |
| 09-用户等级成长积分与外观.md | Growth/Points/Cosmetic |
| 10-第一批Tool开发规范.md | 首批工具 |
| 11-安全与隐私规范.md | 安全 |
| 12-性能与工程质量.md | 性能 |
| 13-测试与验收规范.md | 测试 |
| 14-开发阶段与Agent执行规范.md | Agent执行 |
| 15-完整性检查清单.md | 验收清单 |
| 16-冻结项与待冻结项.md | 冻结状态 |

## 核心结论

```text
vctn-admin-web
      ↓
admin.example.com

vctn-tools-web
      ↓
tools.example.com

FastAPI
      ↓
api.example.com
```

两个前端源码、Router、Store、Layout、View、业务组件、构建和部署完全隔离；通过后端 API Contract 协作。
