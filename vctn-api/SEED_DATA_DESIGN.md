# VCTN Seed Data — 设计说明（SEED_DATA_DESIGN）

本文描述 VCTN 后端（`vctn-api`）PostgreSQL 初始数据的实现设计：目标、边界、幂等机制、
安全约束、权限体系构建方式，以及未冻结项的处理方式。实现代码位于
`app/scripts/seed/`，入口命令 `python -m app.scripts.seed`。

---

## 1. 目标与不变量

Seed 的唯一目的：**把一套新部署的 PostgreSQL 初始化到「可以立刻用」的状态** —— 有根部门、
有内置角色、有完整权限资源树、有唯一可用的超级管理员、有字典/配置/开关/等级/工具/博客分类等
基础目录数据。

必须始终成立的硬不变量：

| 编号 | 不变量 | 实现位置 |
| --- | --- | --- |
| INV-1 | **幂等**：连续执行 1 / 2 / 10 次，结果完全一致，第 2 次起 `created = 0` | `helpers.ensure_row` |
| INV-2 | **不做破坏性操作**：无 `TRUNCATE` / `DROP` / 全表 `DELETE` / 重建库 | 全包仅 `session.add()` |
| INV-3 | **不覆盖已有真实数据**：已存在的行原样返回，`values` 只在 INSERT 时生效 | `ensure_row`（早退分支） |
| INV-4 | **不重置已有管理员密码** | `seed_super_admin` 早退分支 |
| INV-5 | **不写死明文密码**；密码只从环境变量读取，缺失即失败 | `runner.resolve_admin_password` |
| INV-6 | **数据库只存哈希**，且必须用项目既有 `PasswordHasher` | `app.shared.security.password.hash_password` |
| INV-7 | **不引入新密码库 / 新依赖** | 仅用 `pwdlib`（项目既有） |
| INV-8 | **主键必须用现有雪花 ID**，不得 `SERIAL` / `IDENTITY` | `ensure_row` → `app.shared.ids.new_id()` |
| INV-9 | **单次 seed run = 单个事务**，出错整体 `ROLLBACK` | `runner._run_once` |
| INV-10 | 幂等判定只用**稳定业务唯一键**，绝不依赖数据库自增/雪花 ID | `catalog` 中的 `*_code` / `slug` / `permission_code` |
| INV-11 | 系统始终至少保留一个**可用 SUPER_ADMIN** | `seed_super_admin` + 校验 `active_super_admins >= 1` |
| INV-12 | 报告中**不出现**任何密码 / 哈希 / Token / Secret / 连接串 | `report.render_*` 固定文案 |

---

## 2. 目录结构

```
app/scripts/
├── __init__.py
└── seed/
    ├── __init__.py          # 包说明 + SeedError 导出
    ├── __main__.py          # python -m app.scripts.seed
    ├── cli.py               # argparse、退出码、写报告
    ├── runner.py            # 环境变量解析、事务编排、执行 N 次
    ├── errors.py            # SeedError + 稳定错误码
    ├── helpers.py           # SeedCounter / find_one / ensure_row / count_rows
    ├── catalog.py           # 声明式数据（唯一的数据来源）
    ├── system_seed.py       # 系统初始化（生产数据）
    ├── test_seed.py         # 测试数据（仅 --mode=test）
    └── report.py            # 计数、校验、固定报告块渲染
```

设计原则：**数据与流程分离**。`catalog.py` 只有数据（元组/字典），没有逻辑；
`system_seed.py` 只有流程，没有硬编码业务值。新增一条字典项只需要改 `catalog.py`。

---

## 3. 执行命令与退出码

```bash
# 生产系统初始化（唯一应该在正式环境执行的命令）
VCTN_SEED_ADMIN_PASSWORD='<强密码>' python -m app.scripts.seed --mode=system

# 系统初始化 + 测试账号
VCTN_SEED_ADMIN_PASSWORD='<强密码>' VCTN_SEED_TEST_PASSWORD='<强密码>' \
    python -m app.scripts.seed --mode=test

# 幂等性验证（连续执行三次并核对报告）
VCTN_SEED_ADMIN_PASSWORD='<强密码>' python -m app.scripts.seed --mode=system --runs=3
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--mode` | `system` | `system` = 仅生产初始化；`test` = 额外写入测试数据 |
| `--admin-username` | `admin` | 初始超级管理员用户名 |
| `--runs` | `1` | 连续执行的次数（用于幂等验证） |
| `--report-path` | `SEED_DATA_REPORT.md` | Markdown 报告输出路径 |
| `--no-report` | 否 | 不写 Markdown 报告 |

| 退出码 | 含义 |
| --- | --- |
| `0` | `Status = PASS` |
| `1` | 校验未通过（`Integrity` / `Security` / `Idempotency` 有 FAIL） |
| `2` | 前置条件不满足（缺环境变量、未配置数据库） |

稳定错误码：

* `SEED_ADMIN_PASSWORD_REQUIRED` —— 未设置 `VCTN_SEED_ADMIN_PASSWORD`，**必须失败**，不会使用任何默认口令。
* `SEED_TEST_PASSWORD_REQUIRED` —— `--mode=test` 未设置 `VCTN_SEED_TEST_PASSWORD`。
* `DATABASE_NOT_CONFIGURED` —— 未配置 PostgreSQL。
* `SCHEMA_MISSING` / `SEED_TOOL_COMPONENT_MISSING` —— 结构缺失或工具引用了不存在的组件。

---

## 4. 幂等机制

### 4.1 唯一判定键

幂等只依赖**稳定业务唯一键**（与冻结 DDL 的 `lower(...)` 唯一索引一致）：

| 集合 | 业务唯一键 |
| --- | --- |
| 部门 | `department_code` |
| 角色 | `role_code` |
| 权限 | `permission_code` |
| 字典类型 / 项 | `dict_code` / (`dict_type_id`, `item_value`) |
| 系统配置 | `config_key` |
| 功能开关 | `flag_key` |
| 等级 / 成长规则 / 积分规则 | `level_code` / `rule_code` / `rule_code` |
| 装扮 / 任务 / 成就 | `cosmetic_code` / `task_code` / `achievement_code` |
| 工具分类 / 工具 / 版本 | `category_code` / `code`、`slug` / (`tool_id`, `version`) |
| 工具组件 / 访问策略 | `component_key` / (`tool_id`, `subject_type`) |
| 博客分类 | `category_code` |
| 关联表 | 复合主键 (如 `role_id`+`permission_id`) |

### 4.2 写入流程

```
ensure_row(session, Model, keys=…, values=…)
  ├─ find_one(keys)                    # 字符串键统一 lower() 比较，且过滤 deleted_at IS NULL
  ├─ 命中  → 直接返回该行，values 全部丢弃（不 UPDATE、不覆盖用户修改）
  └─ 未命中 → 分配 new_id()（雪花 ID）→ session.add → flush
```

因此：

* 第 1 次运行：`created = N`（全新建库）/ 或仅补齐缺失项；
* 第 2、3 次运行：`created = 0`，`skipped = 全部`。

### 4.3 事务边界

`runner._run_once()` 中：一次 `--runs` 循环体 == 一个 `AsyncSession` == 一个数据库事务。
任何异常都会触发 `await session.rollback()` 并向上抛出，**不会留下半初始化状态**。
校验（`report.verify`）在事务提交之后、用只读会话执行。

---

## 5. 安全约束

| 约束 | 实现 |
| --- | --- |
| 管理员初始密码来自 `VCTN_SEED_ADMIN_PASSWORD` | `runner.resolve_admin_password()`，空值即 `SeedError` |
| 密码先过密码策略再入库 | `validate_password_policy(password, settings)` |
| 只存哈希 | `hash_password()`（`pwdlib` Argon2，项目既有） |
| 密码历史 | 写入 `sys_password_history`（与 `sys_user` 同事务） |
| **不重置已存在管理员密码** | `seed_super_admin` 命中同名用户即早退，仅确保角色绑定 |
| 字段级密码保护 | `sys_permission_field` 中 `password` / `password_hash` 恒为 `HIDDEN` |
| 报告脱敏 | 报告只输出计数与 PASS/FAIL；`Admin Password: NOT SHOWN` |
| 敏感值不落日志 | 密码只在内存中短暂存在，日志/报告均不含密码、哈希、Token、连接串 |

默认管理员账号：

| 属性 | 值 |
| --- | --- |
| `username` | `admin`（可用 `--admin-username` 覆盖） |
| `status` | `ACTIVE` |
| `is_super_admin` | `true` |
| `must_change_password` | `true`（首次登录强制改密） |
| `locked_until` / `deleted_at` | 空 |
| 所属部门 | `SYSTEM`（系统管理部） |
| 角色 | `SUPER_ADMIN`（数据范围 `ALL`） |

---

## 6. 内置角色

| role_code | 名称 | data_scope | 说明 |
| --- | --- | --- | --- |
| `SUPER_ADMIN` | 超级管理员 | `ALL` | 初始获得**全部**权限（不依赖 token，每次查库） |
| `DEPARTMENT_ADMIN` | 部门管理员 | `DEPARTMENT_CHILDREN` | 权限绑定**未冻结** → 暂不授予权限（见 `BLOCKERS.md` B-3） |
| `AUDITOR` | 审计员 | `SELF` | 权限矩阵**未冻结** → 暂不授予权限（见 `BLOCKERS.md` B-4） |

**角色继承**：`sys_role_inheritance` **一行都不写入**。SQL 递归规则未冻结，按规则必须停下报
BLOCKER，而不是自行发明（`BLOCKERS.md` B-2）。

---

## 7. 权限资源体系

`sys_permission` 覆盖 6 种类型，构成一棵可展示的资源树。

| permission_type | 数量 | 父节点 | 说明 |
| --- | --- | --- | --- |
| `MENU` | 8 | 无（根） | 顶级菜单 |
| `PAGE` | 36 | 所属 `MENU` | 页面权限，菜单树完整 |
| `BUTTON` | 40 | 所属 `PAGE` | 只登记规格中真实存在的操作 |
| `API`（业务权限） | 73 | 无 | 见 §7.1 |
| `API`（端点权限） | 200 | 见 §7.2 | 每个真实 HTTP 端点一条 |
| `DATA_SCOPE` | 5 | 无 | `SCOPE_ALL` / `SCOPE_DEPARTMENT` / `SCOPE_DEPARTMENT_CHILDREN` / `SCOPE_SELF` / `SCOPE_CUSTOM` |

### 7.1 业务权限：冻结矩阵为唯一权威

* `catalog.MATRIX_PERMISSIONS`（**64** 条）来自冻结文件
  `aicoding/spec/07-API业务Spec/11-权限矩阵.md`。**这是权限码的唯一权威**，不得重命名或臆造。
* `catalog.RUNTIME_EXTRA_PERMISSIONS`（**9** 条）是控制器里实际 `require_permission("…")`
  了、但**不在冻结矩阵内**的编码：`BLOG_CATEGORY_MANAGE`、`BLOG_COMMENT_REVIEW`、
  `EXPORT_MANAGE`、`LOG_VIEW`、`NOTIFICATION_MANAGE`、`SYSTEM_FILE_MANAGE`、
  `SYSTEM_JOB_MANAGE`、`TOOL_ACCESS_MANAGE`、`TOOL_MANAGE`。
  它们被 seed 出来是为了让权限表与运行代码自洽（否则非超管的授权判断会落到不存在的码上），
  同时**逐条登记到 `BLOCKERS.md` B-1**，绝不静默扩大权限目录。

### 7.2 端点权限：从真实路由 + 真实依赖生成

`permission_code` = `API_{METHOD}_{PATH}`（确定性、稳定、≤128 字符，已核对 200 条无碰撞），
`resource_type = API_ENDPOINT`，`resource_code = "{METHOD} {path}"`。

守护权限映射**不是手写表**，而是从运行中的路由与控制器源码读出：

* `collect_endpoints(api_prefix)`：枚举 `app.openapi()` 中所有 `/api/v1/**` 端点（200 条）。
* `collect_route_guards(api_prefix)`：遍历 `app.main._BUSINESS_ROUTERS`，对每个
  `APIRoute.endpoint` 用 `inspect.getsource` + AST 扫描，提取其声明的
  `require_permission("X")` / `require_any_permission("X","Y")` 字面量。
* 端点权限节点的 `parent_id` 指向其**唯一**守护业务权限（107 条），于是资源树中
  `USER_VIEW → GET /api/v1/admin/users` 这样的从属关系是可查询、可展示的。
  无守护（`Public` / 仅 `Auth`）或守护码多于一个时 `parent_id` 留空。

> 说明：常量 `_BUSINESS_ROUTERS` 是路由装配表，被 seed 只读引用；它不参与权限判定。

### 7.3 字段权限

`sys_permission_field` 挂在对应业务权限下：

| 业务权限 | 字段 | field_mode |
| --- | --- | --- |
| `USER_VIEW` | `phone` / `email` | `VISIBLE` |
| `USER_VIEW` | `password_hash` / `mfa_secret` | `HIDDEN` |
| `USER_EDIT` | `phone` / `email` | `EDITABLE` |
| `USER_EDIT` | `password_hash` / `mfa_secret` | `HIDDEN` |
| `USER_RESET_PASSWORD` | `password_hash` / `mfa_secret` | `HIDDEN` |

`password` / `password_hash` **任何权限下都不会是可见模式**，这是硬约束。

---

## 8. 其他初始化数据

| 集合 | 数量 | 来源 / 备注 |
| --- | --- | --- |
| Departments | 1 | `SYSTEM` 系统管理部（根部门） |
| Dictionaries | 27 类型 / 95 项 | 状态、日志、工具、任务、博客、权限、装扮等枚举 |
| Configs | 38 | **全部取自 `Settings` 的代码默认值**，不臆造业务数值 |
| Feature Flags | 4 | `TOOL_ENABLED` / `BLOG_ENABLED` / `ANALYTICS_ENABLED` = true，`MFA_ENABLED` = false |
| Levels | 1 | 仅 `LV1`（阈值 DD-16 未冻结，见 B-5） |
| Growth Rules | 5 | 绑定真实事件码，`growth_points = 0`、`enabled = false`（未冻结） |
| Point Rules | 5 | 绑定真实事件码，`points = 0`、`enabled = false`（未冻结） |
| Cosmetics | 6 | 六种装扮类型的默认项，不授予任何用户 |
| Tasks | 3 | `status = DISABLED`，`reward = NULL`（奖励未冻结） |
| Achievements | 3 | `status = DISABLED`，`reward = NULL`（奖励未冻结） |
| Tool Categories | 9 | 工具分类目录 |
| Tools | 22 | `component_key` **全部来自** `build_default_registry()` 中真实存在的 provider |
| Tool Versions | 22 | 每个工具 1 条 `1.0.0`，`PUBLISHED`，并回填 `tool.current_version_id` |
| Tool Components | 17 | 由 `build_default_registry()` 枚举生成，**不写任何 Vue import path** |
| Tool Policies | 44 | 每个工具的 `GUEST` / `USER` 两条策略，配额留空（DD 未冻结） |
| Blog Categories | 4 | 技术分享 / 教程指南 / 平台公告 / 行业资讯 |

### 8.1 工具组件为何只能来自 registry

`seed_tools()` 调用 `build_default_registry()`，对 `catalog.TOOLS` 中每个
`component_key` 做存在性校验；一旦引用了后端无法执行的组件，直接抛
`SEED_TOOL_COMPONENT_MISSING` 并整体回滚。因此**不可能**出现「工具指向不存在的组件」。

### 8.2 Analytics 不含任何伪造数据

Seed **不写入**任何行为事件、统计聚合或埋点数据。`configs` 中
`analytics.raw_event_retention_days` 保留期未冻结，写为 `NULL` 并带说明文案。

---

## 9. 测试数据模式

`--mode=test` 在系统初始化之上追加（且仅追加）：

| 对象 | 值 |
| --- | --- |
| 测试管理员 | `testadmin`（`is_super_admin = false`，绑定 `DEPARTMENT_ADMIN`，`must_change_password = true`） |
| 测试业务用户 | `testuser`（`biz_user` + `biz_user_profile` + `biz_user_login_identity` + `biz_user_password_history`） |
| 测试密码 | 只从 `VCTN_SEED_TEST_PASSWORD` 读取，缺失即 `SEED_TEST_PASSWORD_REQUIRED` |

分离性：`--mode=system` **永远不会**创建上述任何一行；测试账号使用 `test*` 前缀，
与生产账号天然可区分。正式环境只执行 `--mode=system`。

---

## 10. 校验矩阵（`report.verify`）

| 校验 | 断言 |
| --- | --- |
| `super_admin_state` | 管理员为 `ACTIVE` + `is_super_admin` + `must_change_password`，未锁定、未删除 |
| `security` | 管理员口令为哈希（长度 > 20 且形如 `$…`） |
| `super_admin_grants` | `SUPER_ADMIN` 的授权数 == 权限总数（362 / 362） |
| `tool_graph_complete` | 每个工具都有分类 + 版本 + 组件 + 策略 + `current_version_id` |
| `levels_present` / `growth_rules_event_bound` / `tasks_event_bound` / `achievements_event_bound` | 目录存在且绑定真实事件/条件 |
| `permission_matrix_complete` | 冻结矩阵 64 条权限码全部存在 |
| `runtime_extra_permissions_present` | 9 条矩阵外编码全部存在（并在 BLOCKERS 登记） |
| `route_guards_known` | 控制器实际使用的 45 个守护码全部存在于权限表 |
| `api_endpoint_coverage` | 200 个真实端点全部有对应 API 权限 |
| `api_permission_tree_linked` | 107 个单一守护端点全部挂到其业务权限下 |

外加独立的数据库层校验（见 `SEED_DATA_REPORT.md` 与最终答复）：业务键唯一性、外键/孤儿、
`SUPER_ADMIN` 全量授权、普通管理员 0 权限、`field_mode` 无泄漏。

---

## 11. 未完成 / 未冻结项

所有「规格未冻结」与「实现与冻结契约存在差异」的条目，一律不擅自发明，集中登记在
`BLOCKERS.md`：角色继承 SQL、AUDITOR/DEPARTMENT_ADMIN 权限绑定、等级阈值、成长/积分值、
任务/成就奖励、Feature Flag 全集、CUSTOM 数据范围、MFA Provider、埋点保留期、
以及 9 条矩阵外权限码与 79 条未实现冻结端点 / 74 条未入册已实现端点。
