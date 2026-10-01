"""The production system seed.

It creates only what a fresh deployment must always contain: the root
department, the built-in roles, the permission resource tree, one usable
``SUPER_ADMIN`` account, dictionaries, configuration mirrors, feature flags, the
level / rule / cosmetic / task / achievement catalogue, the tool catalogue and the
default blog categories.

Nothing here truncates, deletes or rewrites: each row is inserted only when its
stable business key is absent, and an existing administrator's password is never
reset.
"""

from __future__ import annotations

import ast
import datetime
import inspect
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysPasswordHistory
from app.admin.config.model import SysConfig, SysFeatureFlag
from app.admin.departments.model import SysDepartment
from app.admin.dictionaries.model import SysDictItem, SysDictType
from app.admin.permissions.model import SysPermission, SysPermissionField, SysRolePermission
from app.admin.roles.model import SysRole, SysUserRole
from app.admin.users.model import SysUser
from app.blog.categories.model import BlogCategory
from app.core.config import Settings
from app.platform.cosmetics.model import BizCosmetic
from app.platform.growth.model import BizAchievement, BizGrowthRule, BizTask
from app.platform.levels.model import BizUserLevel
from app.platform.points.model import BizPointRule
from app.scripts.seed import catalog
from app.scripts.seed.errors import SeedError
from app.scripts.seed.helpers import SeedCounter, ensure_row, find_one
from app.shared.ids import new_id
from app.shared.security.password import (
    hash_password,
    password_expiry_at,
    validate_password_policy,
)
from app.tools.access.model import ToolAccessPolicy
from app.tools.catalog.model import (
    Tool,
    ToolCategory,
    ToolComponentRegistry,
    ToolVersion,
)
from app.tools.runtime.providers import build_default_registry

ACTIVE: str = "ACTIVE"
SUBJECT_GUEST: str = "GUEST"
SUBJECT_USER: str = "USER"


@dataclass(slots=True)
class SystemSeedResult:
    """References produced by the system seed, reused by the test seed."""

    department: SysDepartment | None = None
    roles: dict[str, SysRole] = field(default_factory=dict)
    permissions: dict[str, SysPermission] = field(default_factory=dict)
    admin: SysUser | None = None


# ---------------------------------------------------------------------------
# Department / roles
# ---------------------------------------------------------------------------
async def seed_departments(session: AsyncSession, counter: SeedCounter) -> SysDepartment:
    department, _ = await ensure_row(
        session,
        SysDepartment,
        keys={"department_code": catalog.DEPARTMENT_CODE},
        values={
            "department_name": "系统管理部",
            "parent_id": None,
            "status": ACTIVE,
            "sort_order": 0,
            "description": "平台最高管理机构",
        },
        counter=counter,
        collection="departments",
    )
    return department


async def seed_roles(session: AsyncSession, counter: SeedCounter) -> dict[str, SysRole]:
    roles: dict[str, SysRole] = {}
    for role_code, role_name, data_scope, description in catalog.ROLES:
        row, _ = await ensure_row(
            session,
            SysRole,
            keys={"role_code": role_code},
            values={
                "role_name": role_name,
                "data_scope": data_scope,
                "status": ACTIVE,
                "description": description,
            },
            counter=counter,
            collection="roles",
        )
        roles[role_code] = row
    return roles


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
def route_permission_code(method: str, path: str) -> str:
    """Return a stable permission code for one HTTP endpoint.

    The code is derived from ``method`` + ``path`` so a scan of the live router
    always yields the same identifier for the same endpoint.
    """
    raw = f"API_{method}_{path}"
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", raw).strip("_").upper()
    return cleaned[:128]


async def seed_permissions(
    session: AsyncSession,
    counter: SeedCounter,
    *,
    endpoints: tuple[tuple[str, str], ...],
    guards: dict[tuple[str, str], tuple[str, ...]] | None = None,
) -> dict[str, SysPermission]:
    """Insert the full permission resource tree and return code -> row."""
    permissions: dict[str, SysPermission] = {}
    route_guards = guards or {}

    async def ensure_permission(
        code: str,
        name: str,
        permission_type: str,
        resource_type: str,
        *,
        resource_code: str | None = None,
        parent: SysPermission | None = None,
        sort_order: int = 0,
    ) -> SysPermission:
        row, _ = await ensure_row(
            session,
            SysPermission,
            keys={"permission_code": code},
            values={
                "permission_name": name,
                "permission_type": permission_type,
                "resource_type": resource_type,
                "resource_code": resource_code,
                "parent_id": None if parent is None else int(parent.id),
                "sort_order": sort_order,
                "status": ACTIVE,
            },
            counter=counter,
            collection="permissions",
        )
        permissions[code] = row
        return row

    # menu / page tree (parents are declared before their children)
    for code, name, parent_code, kind, sort_order in catalog.MENU_NODES:
        parent = permissions.get(parent_code) if parent_code else None
        await ensure_permission(
            code,
            name,
            kind,
            kind,
            parent=parent,
            sort_order=sort_order,
        )

    # buttons hang off a page
    for code, name, parent_page in catalog.BUTTONS:
        await ensure_permission(code, name, "BUTTON", "BUTTON", parent=permissions.get(parent_page))

    # the frozen permission matrix plus the codes the controllers actually
    # enforce (the latter are flagged in BLOCKERS.md)
    for code, name in sorted(catalog.BUSINESS_PERMISSIONS.items()):
        await ensure_permission(code, name, "API", "API")

    # data scope resources
    for code in catalog.SCOPE_PERMISSIONS:
        await ensure_permission(code, code, "DATA_SCOPE", "DATA_SCOPE")

    # endpoint coverage: one API resource per live endpoint, attached to the
    # business permission the controller actually enforces (``parent_id``).
    for method, path in endpoints:
        code = route_permission_code(method, path)
        enforced = route_guards.get((method, path), ())
        owner = permissions.get(enforced[0]) if len(enforced) == 1 else None
        await ensure_permission(
            code,
            f"{method} {path}",
            "API",
            "API_ENDPOINT",
            resource_code=f"{method} {path}",
            parent=owner,
        )

    # field level control on sensitive columns
    for permission_code, fields in catalog.FIELD_PERMISSIONS.items():
        owner = permissions.get(permission_code)
        if owner is None:
            continue
        for field_code, field_mode in fields:
            await ensure_row(
                session,
                SysPermissionField,
                keys={"permission_id": int(owner.id), "field_code": field_code},
                values={"field_mode": field_mode},
                counter=counter,
                collection="permission_fields",
            )

    return permissions


async def grant_permissions(
    session: AsyncSession,
    counter: SeedCounter,
    *,
    role: SysRole,
    permissions: dict[str, SysPermission],
) -> int:
    """Grant every permission to a role (used for SUPER_ADMIN)."""
    granted = 0
    for permission in permissions.values():
        _, created = await ensure_row(
            session,
            SysRolePermission,
            keys={"role_id": int(role.id), "permission_id": int(permission.id)},
            counter=counter,
            collection="role_permissions",
        )
        granted += 1 if created else 0
    return granted


# ---------------------------------------------------------------------------
# Super administrator
# ---------------------------------------------------------------------------
async def seed_super_admin(
    session: AsyncSession,
    settings: Settings,
    counter: SeedCounter,
    *,
    department: SysDepartment,
    role: SysRole,
    username: str,
    password: str,
) -> SysUser:
    """Create the initial ``SUPER_ADMIN`` account once.

    The password material is read from the environment by the CLI, validated
    against the frozen policy and stored only as a hash. An existing account is
    returned untouched: its password is never reset.
    """
    existing = await find_one(session, SysUser, username=username)
    if existing is not None:
        counter.skipped_one("admin")
        await ensure_row(
            session,
            SysUserRole,
            keys={"user_id": int(existing.id), "role_id": int(role.id)},
            counter=counter,
            collection="user_roles",
        )
        return existing

    validate_password_policy(password, settings)
    now = datetime.datetime.now(datetime.UTC)
    password_hash = hash_password(password)
    user = SysUser(
        id=new_id(),
        username=username,
        password_hash=password_hash,
        display_name="超级管理员",
        department_id=int(department.id),
        status=ACTIVE,
        is_super_admin=True,
        must_change_password=True,
        password_changed_at=now,
        password_expires_at=password_expiry_at(now, settings),
        failed_login_count=0,
    )
    session.add(user)
    await session.flush()
    session.add(SysPasswordHistory(id=new_id(), user_id=int(user.id), password_hash=password_hash))
    await session.flush()
    counter.created_one("admin")

    await ensure_row(
        session,
        SysUserRole,
        keys={"user_id": int(user.id), "role_id": int(role.id)},
        counter=counter,
        collection="user_roles",
    )
    return user


# ---------------------------------------------------------------------------
# Dictionaries / configuration / flags
# ---------------------------------------------------------------------------
async def seed_dictionaries(session: AsyncSession, counter: SeedCounter) -> None:
    for type_code, type_name, items in catalog.DICT_TYPES:
        dict_type, _ = await ensure_row(
            session,
            SysDictType,
            keys={"dict_code": type_code},
            values={"dict_name": type_name, "status": ACTIVE},
            counter=counter,
            collection="dict_types",
        )
        for value, label, sort_order, is_default in items:
            await ensure_row(
                session,
                SysDictItem,
                keys={"dict_type_id": int(dict_type.id), "item_value": value},
                values={
                    "item_label": label,
                    "item_code": value,
                    "sort_order": sort_order,
                    "is_default": is_default,
                    "status": ACTIVE,
                },
                counter=counter,
                collection="dict_items",
            )


def _config_rows(settings: Settings) -> tuple[tuple[str, str, str, str, Any], ...]:
    """Return the configuration mirror rows.

    Every value is the code default from :class:`Settings`; no business number is
    invented. ``value_type`` is one of ``INT`` / ``BOOL`` / ``STRING``.
    """
    s = settings
    return (
        (
            "password.min_length", "密码最小长度",
            "PASSWORD", "INT", s.PASSWORD_MIN_LENGTH,
        ),
        (
            "password.require_uppercase", "密码需大写字母",
            "PASSWORD", "BOOL", s.PASSWORD_REQUIRE_UPPERCASE,
        ),
        (
            "password.require_lowercase", "密码需小写字母",
            "PASSWORD", "BOOL", s.PASSWORD_REQUIRE_LOWERCASE,
        ),
        (
            "password.require_digit", "密码需数字",
            "PASSWORD", "BOOL", s.PASSWORD_REQUIRE_DIGIT,
        ),
        (
            "password.require_special", "密码需特殊字符",
            "PASSWORD", "BOOL", s.PASSWORD_REQUIRE_SPECIAL,
        ),
        (
            "password.history_count", "密码历史数量",
            "PASSWORD", "INT", s.PASSWORD_HISTORY_COUNT,
        ),
        (
            "password.expire_days", "密码有效期（天）",
            "PASSWORD", "INT", s.PASSWORD_EXPIRE_DAYS,
        ),
        (
            "password.max_failed_attempts", "最大登录失败次数",
            "PASSWORD", "INT", s.PASSWORD_MAX_FAILED_ATTEMPTS,
        ),
        (
            "password.lock_minutes", "锁定时长（分钟）",
            "PASSWORD", "INT", s.PASSWORD_LOCK_MINUTES,
        ),
        (
            "session.access_token_ttl_seconds", "访问令牌有效期（秒）",
            "SESSION", "INT", s.AUTH_ACCESS_TOKEN_TTL_SECONDS,
        ),
        (
            "session.refresh_token_ttl_seconds", "刷新令牌有效期（秒）",
            "SESSION", "INT", s.AUTH_REFRESH_TOKEN_TTL_SECONDS,
        ),
        (
            "session.max_active_sessions_per_user", "单用户最大会话数",
            "SESSION", "INT", s.AUTH_MAX_ACTIVE_SESSIONS_PER_USER,
        ),
        (
            "security.jwt_algorithm", "JWT 算法",
            "SECURITY", "STRING", s.AUTH_JWT_ALGORITHM,
        ),
        (
            "security.jwt_issuer", "JWT 签发者",
            "SECURITY", "STRING", s.AUTH_ISSUER,
        ),
        (
            "security.audit_enabled", "审计开关",
            "SECURITY", "BOOL", s.AUDIT_ENABLED,
        ),
        (
            "audit.retention_days", "审计日志保留（天）",
            "AUDIT", "INT", s.LOG_RETENTION_AUDIT_LOG_DAYS,
        ),
        (
            "log.retention.access_days", "访问日志保留（天）",
            "LOG", "INT", s.LOG_RETENTION_ACCESS_LOG_DAYS,
        ),
        (
            "log.retention.security_days", "安全日志保留（天）",
            "LOG", "INT", s.LOG_RETENTION_SECURITY_LOG_DAYS,
        ),
        (
            "log.retention.operation_days", "操作日志保留（天）",
            "LOG", "INT", s.LOG_RETENTION_OPERATION_LOG_DAYS,
        ),
        (
            "log.retention.audit_days", "审计日志保留（天）",
            "LOG", "INT", s.LOG_RETENTION_AUDIT_LOG_DAYS,
        ),
        (
            "log.retention.application_days", "应用日志保留（天）",
            "LOG", "INT", s.LOG_RETENTION_APPLICATION_LOG_DAYS,
        ),
        (
            "tool.guest_daily_quota", "游客每日配额",
            "TOOL", "INT", s.TOOL_GUEST_DAILY_QUOTA,
        ),
        (
            "tool.user_daily_quota", "用户每日配额",
            "TOOL", "INT", s.TOOL_USER_DAILY_QUOTA,
        ),
        (
            "rate_limit.enabled", "限流开关",
            "RATE_LIMIT", "BOOL", s.RATE_LIMIT_ENABLED,
        ),
        (
            "rate_limit.window_seconds", "限流窗口（秒）",
            "RATE_LIMIT", "INT", s.RATE_LIMIT_WINDOW_SECONDS,
        ),
        (
            "rate_limit.login_per_window", "登录限流次数",
            "RATE_LIMIT", "INT", s.RATE_LIMIT_LOGIN_PER_WINDOW,
        ),
        (
            "rate_limit.api_per_window", "接口限流次数",
            "RATE_LIMIT", "INT", s.RATE_LIMIT_API_PER_WINDOW,
        ),
        (
            "export.max_rows", "导出行数上限",
            "EXPORT", "INT", s.EXPORT_MAX_ROWS,
        ),
        (
            "export.retention_days", "导出文件保留（天）",
            "EXPORT", "INT", s.EXPORT_RETENTION_DAYS,
        ),
        (
            "file.storage_provider", "文件存储提供方",
            "FILE", "STRING", s.FILE_STORAGE_PROVIDER,
        ),
        (
            "file.max_size_bytes", "文件大小上限（字节）",
            "FILE", "INT", s.FILE_MAX_SIZE_BYTES,
        ),
        (
            "verification.code_ttl_seconds", "验证码有效期（秒）",
            "VERIFICATION", "INT", s.VERIFICATION_CODE_TTL_SECONDS,
        ),
        (
            "verification.code_length", "验证码长度",
            "VERIFICATION", "INT", s.VERIFICATION_CODE_LENGTH,
        ),
        (
            "idempotency.ttl_seconds", "幂等键有效期（秒）",
            "IDEMPOTENCY", "INT", s.IDEMPOTENCY_TTL_SECONDS,
        ),
        (
            "outbox.enabled", "Outbox 开关",
            "OUTBOX", "BOOL", s.OUTBOX_ENABLED,
        ),
        (
            "outbox.batch_size", "Outbox 批量大小",
            "OUTBOX", "INT", s.OUTBOX_BATCH_SIZE,
        ),
        (
            "outbox.max_attempts", "Outbox 最大重试",
            "OUTBOX", "INT", s.OUTBOX_MAX_ATTEMPTS,
        ),
        (
            "analytics.raw_event_retention_days", "原始埋点保留（天，未冻结）",
            "ANALYTICS", "INT", None,
        ),
    )


async def seed_configs(
    session: AsyncSession, counter: SeedCounter, *, settings: Settings
) -> None:
    for key, name, group, value_type, value in _config_rows(settings):
        rendered = None if value is None else str(value)
        await ensure_row(
            session,
            SysConfig,
            keys={"config_key": key},
            values={
                "config_name": name,
                "config_group": group,
                "value_type": value_type,
                "config_value": rendered,
                "default_value": rendered,
                "editable": True,
                "requires_restart": False,
                "status": ACTIVE,
                "description": "未冻结，使用代码默认值" if value is None else None,
            },
            counter=counter,
            collection="configs",
        )


async def seed_feature_flags(session: AsyncSession, counter: SeedCounter) -> None:
    for flag_key, flag_name, enabled, description in catalog.FEATURE_FLAGS:
        await ensure_row(
            session,
            SysFeatureFlag,
            keys={"flag_key": flag_key},
            values={
                "flag_name": flag_name,
                "enabled": enabled,
                "strategy": "GLOBAL",
                "description": description,
            },
            counter=counter,
            collection="feature_flags",
        )


# ---------------------------------------------------------------------------
# Growth / points / levels / cosmetics / tasks / achievements
# ---------------------------------------------------------------------------
async def seed_levels(session: AsyncSession, counter: SeedCounter) -> None:
    for level_code, level_name, level_no, min_growth in catalog.LEVELS:
        await ensure_row(
            session,
            BizUserLevel,
            keys={"level_code": level_code},
            values={
                "level_name": level_name,
                "level_no": level_no,
                "min_growth_points": min_growth,
                "status": ACTIVE,
                "sort_order": level_no,
                "description": "等级阈值未冻结（DD-16），仅初始化基础等级",
            },
            counter=counter,
            collection="levels",
        )


async def seed_growth_rules(session: AsyncSession, counter: SeedCounter) -> None:
    for rule_code, rule_name, event_code in catalog.GROWTH_RULES:
        await ensure_row(
            session,
            BizGrowthRule,
            keys={"rule_code": rule_code},
            values={
                "rule_name": rule_name,
                "event_code": event_code,
                "growth_points": 0,
                "enabled": False,
                "description": "成长值未冻结（DD-16），默认不启用",
            },
            counter=counter,
            collection="growth_rules",
        )


async def seed_point_rules(session: AsyncSession, counter: SeedCounter) -> None:
    for rule_code, rule_name, event_code in catalog.POINT_RULES:
        await ensure_row(
            session,
            BizPointRule,
            keys={"rule_code": rule_code},
            values={
                "rule_name": rule_name,
                "event_code": event_code,
                "points": 0,
                "enabled": False,
                "description": "积分值未冻结（DD-16），默认不启用",
            },
            counter=counter,
            collection="point_rules",
        )


async def seed_cosmetics(session: AsyncSession, counter: SeedCounter) -> None:
    for cosmetic_code, cosmetic_name, cosmetic_type, sort_order in catalog.COSMETICS:
        await ensure_row(
            session,
            BizCosmetic,
            keys={"cosmetic_code": cosmetic_code},
            values={
                "cosmetic_name": cosmetic_name,
                "cosmetic_type": cosmetic_type,
                "status": ACTIVE,
                "sort_order": sort_order,
            },
            counter=counter,
            collection="cosmetics",
        )


async def seed_tasks(session: AsyncSession, counter: SeedCounter) -> None:
    for task_code, task_name, task_type, conditions in catalog.TASKS:
        await ensure_row(
            session,
            BizTask,
            keys={"task_code": task_code},
            values={
                "task_name": task_name,
                "task_type": task_type,
                "conditions": conditions,
                "reward": None,
                "repeatable": False,
                "status": "DISABLED",
            },
            counter=counter,
            collection="tasks",
        )


async def seed_achievements(session: AsyncSession, counter: SeedCounter) -> None:
    for achievement_code, achievement_name, conditions in catalog.ACHIEVEMENTS:
        await ensure_row(
            session,
            BizAchievement,
            keys={"achievement_code": achievement_code},
            values={
                "achievement_name": achievement_name,
                "conditions": conditions,
                "reward": None,
                "status": "DISABLED",
            },
            counter=counter,
            collection="achievements",
        )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
async def seed_tools(session: AsyncSession, counter: SeedCounter) -> None:
    """Seed the tool catalogue from the providers the backend can actually run."""
    registry = build_default_registry()

    for component_key in registry.keys():
        provider = registry.get(component_key)
        if provider is None:  # pragma: no cover - keys() and get() agree
            continue
        await ensure_row(
            session,
            ToolComponentRegistry,
            keys={"component_key": component_key},
            values={
                "component_name": component_key,
                "frontend_component_key": component_key,
                "execution_mode": str(provider.execution_mode),
                "status": ACTIVE,
            },
            counter=counter,
            collection="tool_components",
        )

    categories: dict[str, ToolCategory] = {}
    for category_code, category_name, sort_order in catalog.TOOL_CATEGORIES:
        row, _ = await ensure_row(
            session,
            ToolCategory,
            keys={"category_code": category_code},
            values={
                "category_name": category_name,
                "sort_order": sort_order,
                "status": ACTIVE,
            },
            counter=counter,
            collection="tool_categories",
        )
        categories[category_code] = row

    for index, entry in enumerate(catalog.TOOLS):
        code, name, slug, category_code, component_key, summary = entry
        provider = registry.get(component_key)
        if provider is None:
            raise SeedError(
                f"tool '{code}' references an unregistered component '{component_key}'",
                code="SEED_TOOL_COMPONENT_MISSING",
            )
        category = categories[category_code]
        tool, _ = await ensure_row(
            session,
            Tool,
            keys={"code": code},
            values={
                "name": name,
                "slug": slug,
                "category_id": int(category.id),
                "component_key": component_key,
                "execution_mode": str(provider.execution_mode),
                "status": ACTIVE,
                "sort_order": (index + 1) * 10,
                "summary": summary,
                "keywords": [code, name, component_key],
                "tags": [category_code],
            },
            counter=counter,
            collection="tools",
        )

        version, _ = await ensure_row(
            session,
            ToolVersion,
            keys={"tool_id": int(tool.id), "version": "1.0.0"},
            values={
                "release_status": "PUBLISHED",
                "changelog": "initial seed version",
                "published_at": datetime.datetime.now(datetime.UTC),
            },
            counter=counter,
            collection="tool_versions",
        )
        if tool.current_version_id is None:
            tool.current_version_id = int(version.id)
            await session.flush()

        for subject_type in (SUBJECT_GUEST, SUBJECT_USER):
            await ensure_row(
                session,
                ToolAccessPolicy,
                keys={"tool_id": int(tool.id), "subject_type": subject_type},
                values={
                    "enabled": True,
                    "daily_limit": None,
                    "rate_limit_per_minute": None,
                    "concurrency_limit": None,
                },
                counter=counter,
                collection="tool_policies",
            )


# ---------------------------------------------------------------------------
# Blog
# ---------------------------------------------------------------------------
async def seed_blog(session: AsyncSession, counter: SeedCounter) -> None:
    for category_code, category_name, sort_order in catalog.BLOG_CATEGORIES:
        await ensure_row(
            session,
            BlogCategory,
            keys={"category_code": category_code},
            values={
                "category_name": category_name,
                "sort_order": sort_order,
                "status": ACTIVE,
            },
            counter=counter,
            collection="blog_categories",
        )


_HTTP_METHODS: Final[frozenset[str]] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

_GUARD_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"require_permission", "require_any_permission"}
)


def collect_endpoints(api_prefix: str) -> tuple[tuple[str, str], ...]:
    """Return ``(method, path)`` for every business endpoint of the live app.

    The OpenAPI schema is used rather than ``app.routes`` because included
    routers are not flattened into ``APIRoute`` objects in this FastAPI build.
    Imported lazily so the seed does not build the whole application unless it
    actually needs the permission coverage list.
    """
    from app.main import app as fastapi_app

    schema = fastapi_app.openapi()
    endpoints: set[tuple[str, str]] = set()
    for path, operations in schema.get("paths", {}).items():
        if not path.startswith(api_prefix):
            continue
        for method in operations:
            upper = method.upper()
            if upper in _HTTP_METHODS:
                endpoints.add((upper, path))
    return tuple(sorted(endpoints))


def _guard_codes(handler_source: str) -> tuple[str, ...]:
    """Collect the literal permission codes one handler declares as dependencies."""
    found: set[str] = set()
    tree = ast.parse(textwrap.dedent(handler_source))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", None)
        if name not in _GUARD_FUNCTIONS:
            continue
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                found.add(argument.value)
    return tuple(sorted(found))


def collect_route_guards(api_prefix: str) -> dict[tuple[str, str], tuple[str, ...]]:
    """Map every mounted endpoint to the permission codes its handler declares.

    The mapping is read from the controller sources, so it always reflects the
    running router wiring instead of a hand-maintained table.
    """
    from app.main import _BUSINESS_ROUTERS  # noqa: PLC0415 - private wiring table

    guards: dict[tuple[str, str], tuple[str, ...]] = {}
    for prefix, _tag, router in _BUSINESS_ROUTERS:
        for route in router.routes:
            declared = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            endpoint = getattr(route, "endpoint", None)
            if declared is None or not methods or endpoint is None:
                continue
            try:
                handler_source = inspect.getsource(endpoint)
            except (OSError, TypeError):  # pragma: no cover - dynamic endpoints
                continue
            codes = _guard_codes(handler_source)
            for method in methods:
                upper = str(method).upper()
                if upper in _HTTP_METHODS:
                    guards[(upper, f"{api_prefix}{prefix}{declared}")] = codes
    return guards


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
async def seed_system(
    session: AsyncSession,
    settings: Settings,
    counter: SeedCounter,
    *,
    admin_username: str,
    admin_password: str,
) -> SystemSeedResult:
    """Run the whole system seed in the caller's transaction."""
    result = SystemSeedResult()

    result.department = await seed_departments(session, counter)
    result.roles = await seed_roles(session, counter)
    result.permissions = await seed_permissions(
        session,
        counter,
        endpoints=collect_endpoints(settings.API_PREFIX),
        guards=collect_route_guards(settings.API_PREFIX),
    )
    await grant_permissions(
        session,
        counter,
        role=result.roles[catalog.ROLE_SUPER_ADMIN],
        permissions=result.permissions,
    )
    result.admin = await seed_super_admin(
        session,
        settings,
        counter,
        department=result.department,
        role=result.roles[catalog.ROLE_SUPER_ADMIN],
        username=admin_username,
        password=admin_password,
    )

    await seed_dictionaries(session, counter)
    await seed_configs(session, counter, settings=settings)
    await seed_feature_flags(session, counter)
    await seed_levels(session, counter)
    await seed_growth_rules(session, counter)
    await seed_point_rules(session, counter)
    await seed_cosmetics(session, counter)
    await seed_tasks(session, counter)
    await seed_achievements(session, counter)
    await seed_tools(session, counter)
    await seed_blog(session, counter)

    return result


__all__ = [
    "SystemSeedResult",
    "collect_endpoints",
    "collect_route_guards",
    "grant_permissions",
    "route_permission_code",
    "seed_system",
]
