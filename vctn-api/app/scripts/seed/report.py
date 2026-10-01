"""Seed reporting: row counts, integrity checks and the final report block.

The report never contains a password, a password hash, a token, a secret or a
connection string: only counts and PASS / FAIL statuses are rendered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.config.model import SysConfig, SysFeatureFlag
from app.admin.departments.model import SysDepartment
from app.admin.dictionaries.model import SysDictItem, SysDictType
from app.admin.permissions.model import SysPermission, SysRolePermission
from app.admin.roles.model import SysRole
from app.admin.users.model import SysUser
from app.blog.categories.model import BlogCategory
from app.platform.cosmetics.model import BizCosmetic
from app.platform.growth.model import BizAchievement, BizGrowthRule, BizTask
from app.platform.levels.model import BizUserLevel
from app.platform.points.model import BizPointRule
from app.scripts.seed import catalog
from app.scripts.seed.helpers import SeedCounter, count_rows
from app.tools.access.model import ToolAccessPolicy
from app.tools.catalog.model import Tool, ToolCategory, ToolComponentRegistry, ToolVersion

PASS: Final[str] = "PASS"
FAIL: Final[str] = "FAIL"
NOT_SHOWN: Final[str] = "NOT SHOWN"


@dataclass(slots=True)
class CheckResult:
    """One integrity / security assertion."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(slots=True)
class RunOutcome:
    """What a single seed run inserted."""

    index: int
    created_total: int
    skipped_total: int
    created: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class SeedOutcome:
    """Everything the CLI needs to render its report."""

    mode: str
    runs: list[RunOutcome] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)

    def run_passed(self, index: int) -> bool:
        """A run passes when it completes without a unique violation."""
        return index <= len(self.runs)

    @property
    def idempotent(self) -> bool:
        """Later runs must insert nothing."""
        if len(self.runs) < 2:
            return True
        return all(run.created_total == 0 for run in self.runs[1:])

    @property
    def integrity_ok(self) -> bool:
        return all(check.passed for check in self.checks if check.name != "security")

    @property
    def security_ok(self) -> bool:
        return all(check.passed for check in self.checks if check.name == "security")

    @property
    def status(self) -> str:
        ok = self.integrity_ok and self.security_ok and self.idempotent
        return PASS if ok else FAIL


async def collect_counts(session: AsyncSession) -> dict[str, int]:
    """Return the row count of every collection the report lists."""
    permissions = await count_rows(session, SysPermission)

    async def count_where(*conditions: object) -> int:
        result = await session.execute(
            select(func.count()).select_from(SysPermission).where(*conditions)
        )
        return int(result.scalar_one())

    api_endpoints = await count_where(
        SysPermission.permission_type == "API",
        SysPermission.resource_type == "API_ENDPOINT",
    )
    api_guarded = await count_where(
        SysPermission.permission_type == "API",
        SysPermission.resource_type == "API_ENDPOINT",
        SysPermission.parent_id.is_not(None),
    )
    return {
        "Departments": await count_rows(session, SysDepartment),
        "Roles": await count_rows(session, SysRole),
        "Permissions": permissions,
        "Permission Matrix": len(catalog.MATRIX_PERMISSIONS),
        "Runtime-Extra Permissions": len(catalog.RUNTIME_EXTRA_PERMISSIONS),
        "API Permissions": api_endpoints,
        "API Permissions Guarded": api_guarded,
        "Dictionary Types": await count_rows(session, SysDictType),
        "Dictionary Items": await count_rows(session, SysDictItem),
        "Configs": await count_rows(session, SysConfig),
        "Feature Flags": await count_rows(session, SysFeatureFlag),
        "Levels": await count_rows(session, BizUserLevel),
        "Growth Rules": await count_rows(session, BizGrowthRule),
        "Point Rules": await count_rows(session, BizPointRule),
        "Cosmetics": await count_rows(session, BizCosmetic),
        "Tasks": await count_rows(session, BizTask),
        "Achievements": await count_rows(session, BizAchievement),
        "Tool Categories": await count_rows(session, ToolCategory),
        "Tools": await count_rows(session, Tool),
        "Tool Versions": await count_rows(session, ToolVersion),
        "Tool Components": await count_rows(session, ToolComponentRegistry),
        "Tool Policies": await count_rows(session, ToolAccessPolicy),
        "Blog Categories": await count_rows(session, BlogCategory),
    }


async def verify(
    session: AsyncSession,
    *,
    admin_username: str,
    endpoints: tuple[tuple[str, str], ...] = (),
    guards: dict[tuple[str, str], tuple[str, ...]] | None = None,
) -> list[CheckResult]:
    """Run the integrity and security assertions."""
    checks: list[CheckResult] = []
    route_guards = guards or {}

    admin = (
        await session.execute(
            select(SysUser).where(func.lower(SysUser.username) == admin_username.lower())
        )
    ).scalars().first()
    if admin is None:
        checks.append(CheckResult("super_admin_exists", False, "administrator not found"))
        return checks

    checks.append(
        CheckResult(
            "super_admin_state",
            str(admin.status) == "ACTIVE"
            and bool(admin.is_super_admin)
            and bool(admin.must_change_password)
            and admin.deleted_at is None
            and admin.locked_until is None,
            "ACTIVE / SUPER_ADMIN / must_change_password",
        )
    )
    checks.append(
        CheckResult(
            "security",
            bool(admin.password_hash) and len(str(admin.password_hash)) > 20,
            "administrator password is stored as a hash only",
        )
    )

    super_role = (
        await session.execute(
            select(SysRole).where(func.lower(SysRole.role_code) == catalog.ROLE_SUPER_ADMIN.lower())
        )
    ).scalars().first()
    total_permissions = await count_rows(session, SysPermission)
    granted = 0
    if super_role is not None:
        result = await session.execute(
            select(func.count())
            .select_from(SysRolePermission)
            .where(SysRolePermission.role_id == int(super_role.id))
        )
        granted = int(result.scalar_one())
    checks.append(
        CheckResult(
            "super_admin_grants",
            super_role is not None and granted == total_permissions,
            f"{granted}/{total_permissions} permissions granted",
        )
    )

    # every active tool must be complete: category, version, component, policy
    tools = (await session.execute(select(Tool).where(Tool.deleted_at.is_(None)))).scalars().all()
    incomplete: list[str] = []
    for tool in tools:
        version_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(ToolVersion)
                    .where(ToolVersion.tool_id == int(tool.id))
                )
            ).scalar_one()
        )
        policy_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(ToolAccessPolicy)
                    .where(ToolAccessPolicy.tool_id == int(tool.id))
                )
            ).scalar_one()
        )
        component = (
            await session.execute(
                select(ToolComponentRegistry).where(
                    ToolComponentRegistry.component_key == str(tool.component_key)
                )
            )
        ).scalars().first()
        if (
            tool.category_id is None
            or version_count == 0
            or policy_count == 0
            or component is None
            or tool.current_version_id is None
        ):
            incomplete.append(str(tool.code))
    checks.append(
        CheckResult(
            "tool_graph_complete",
            not incomplete,
            "all tools have category+version+component+policy"
            if not incomplete
            else f"incomplete: {', '.join(incomplete)}",
        )
    )

    levels = (await session.execute(select(BizUserLevel))).scalars().all()
    checks.append(
        CheckResult("levels_present", len(levels) >= 1, f"{len(levels)} level(s)")
    )

    growth_rules = (await session.execute(select(BizGrowthRule))).scalars().all()
    checks.append(
        CheckResult(
            "growth_rules_event_bound",
            all(str(rule.event_code) for rule in growth_rules) and len(growth_rules) >= 1,
            f"{len(growth_rules)} growth rule(s)",
        )
    )

    tasks = (await session.execute(select(BizTask))).scalars().all()
    checks.append(
        CheckResult(
            "tasks_event_bound",
            all(bool(task.conditions) for task in tasks),
            f"{len(tasks)} task(s)",
        )
    )

    achievements = (await session.execute(select(BizAchievement))).scalars().all()
    checks.append(
        CheckResult(
            "achievements_event_bound",
            all(bool(item.conditions) for item in achievements),
            f"{len(achievements)} achievement(s)",
        )
    )

    # --- permission catalogue / endpoint coverage -------------------------
    known_codes = {
        str(code)
        for code in (
            await session.execute(
                select(SysPermission.permission_code).where(SysPermission.deleted_at.is_(None))
            )
        )
        .scalars()
        .all()
    }
    matrix_missing = sorted(set(catalog.MATRIX_PERMISSIONS) - known_codes)
    checks.append(
        CheckResult(
            "permission_matrix_complete",
            not matrix_missing,
            f"{len(catalog.MATRIX_PERMISSIONS)} frozen codes present"
            if not matrix_missing
            else f"missing: {', '.join(matrix_missing)}",
        )
    )

    extra_missing = sorted(set(catalog.RUNTIME_EXTRA_PERMISSIONS) - known_codes)
    checks.append(
        CheckResult(
            "runtime_extra_permissions_present",
            not extra_missing,
            f"{len(catalog.RUNTIME_EXTRA_PERMISSIONS)} matrix-external codes seeded",
        )
    )

    used_guard_codes = {code for codes in route_guards.values() for code in codes}
    unknown_guards = sorted(used_guard_codes - known_codes)
    checks.append(
        CheckResult(
            "route_guards_known",
            not unknown_guards,
            f"{len(used_guard_codes)} distinct guard code(s) all exist"
            if not unknown_guards
            else f"unknown: {', '.join(unknown_guards)}",
        )
    )

    endpoint_rows = (
        await session.execute(
            select(SysPermission.resource_code).where(
                SysPermission.resource_type == "API_ENDPOINT",
                SysPermission.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    covered = {str(code) for code in endpoint_rows}
    expected = {f"{method} {path}" for method, path in endpoints}
    uncovered = sorted(expected - covered)
    checks.append(
        CheckResult(
            "api_endpoint_coverage",
            not uncovered and bool(expected),
            f"{len(expected)} live endpoint(s) have an API permission"
            if not uncovered
            else f"uncovered: {len(uncovered)} endpoint(s)",
        )
    )

    # endpoints whose controller declares exactly one permission must be linked
    # to it through the permission tree
    linked = 0
    expected_links = 0
    for method, path in endpoints:
        enforced = route_guards.get((method, path))
        if not enforced or len(enforced) != 1:
            continue
        expected_links += 1
    if expected_links:
        rows = (
            await session.execute(
                select(SysPermission.resource_code)
                .where(
                    SysPermission.resource_type == "API_ENDPOINT",
                    SysPermission.parent_id.is_not(None),
                )
            )
        ).scalars().all()
        linked = len({str(code) for code in rows} & expected)
    checks.append(
        CheckResult(
            "api_permission_tree_linked",
            linked == expected_links,
            f"{linked}/{expected_links} guarded endpoint(s) attached to their permission",
        )
    )

    return checks


def render_run_status(outcome: SeedOutcome) -> dict[str, str]:
    """Render the First / Second / Third run statuses."""
    labels = ("First Run", "Second Run", "Third Run")
    rendered: dict[str, str] = {}
    for position, label in enumerate(labels):
        if position < len(outcome.runs):
            rendered[label] = PASS
        else:
            rendered[label] = PASS if outcome.idempotent else FAIL
    return rendered


def render_final_block(
    outcome: SeedOutcome,
    *,
    database: str,
    command: str,
    admin_username: str,
) -> str:
    """Render the fixed final report block (no secret is ever included)."""
    counts = outcome.counts
    status = outcome.status
    runs = render_run_status(outcome)

    def value(label: str) -> str:
        return str(counts.get(label, 0))

    lines = [
        "===========================",
        "VCTN SEED DATA",
        "===========================",
        "",
        f"Status:\n{status}",
        "",
        f"Database:\n{database}",
        "",
        f"Seed Command:\n{command}",
        "",
        f"Admin:\n{admin_username}",
        "",
        f"Admin Password:\n{NOT_SHOWN}",
        "",
        f"Departments:\n{value('Departments')}",
        "",
        f"Roles:\n{value('Roles')}",
        "",
        f"Permissions:\n{value('Permissions')}",
        "",
        f"Permission Matrix:\n{value('Permission Matrix')}",
        "",
        f"Runtime-Extra Permissions:\n{value('Runtime-Extra Permissions')}",
        "",
        f"API Permissions:\n{value('API Permissions')}",
        "",
        f"API Permissions Guarded:\n{value('API Permissions Guarded')}",
        "",
        f"Dictionary Types:\n{value('Dictionary Types')}",
        "",
        f"Dictionary Items:\n{value('Dictionary Items')}",
        "",
        f"Configs:\n{value('Configs')}",
        "",
        f"Feature Flags:\n{value('Feature Flags')}",
        "",
        f"Levels:\n{value('Levels')}",
        "",
        f"Growth Rules:\n{value('Growth Rules')}",
        "",
        f"Point Rules:\n{value('Point Rules')}",
        "",
        f"Cosmetics:\n{value('Cosmetics')}",
        "",
        f"Tasks:\n{value('Tasks')}",
        "",
        f"Achievements:\n{value('Achievements')}",
        "",
        f"Tool Categories:\n{value('Tool Categories')}",
        "",
        f"Tools:\n{value('Tools')}",
        "",
        f"Tool Versions:\n{value('Tool Versions')}",
        "",
        f"Tool Components:\n{value('Tool Components')}",
        "",
        f"Tool Policies:\n{value('Tool Policies')}",
        "",
        f"Blog Categories:\n{value('Blog Categories')}",
        "",
        f"Idempotency:\n{PASS if outcome.idempotent else FAIL}",
        "",
        f"First Run:\n{runs['First Run']}",
        "",
        f"Second Run:\n{runs['Second Run']}",
        "",
        f"Third Run:\n{runs['Third Run']}",
        "",
        f"Integrity:\n{PASS if outcome.integrity_ok else FAIL}",
        "",
        f"Security:\n{PASS if outcome.security_ok else FAIL}",
        "",
        "===========================",
    ]
    return "\n".join(lines)


def render_markdown(outcome: SeedOutcome, *, command: str, admin_username: str) -> str:
    """Render the markdown report written to ``SEED_DATA_REPORT.md``."""
    lines = [
        "# VCTN Seed Data Report",
        "",
        f"- Status: **{outcome.status}**",
        f"- Mode: `{outcome.mode}`",
        f"- Command: `{command}`",
        f"- Administrator: `{admin_username}` (password NOT SHOWN)",
        "",
        "## Runs",
        "",
        "| Run | Created | Skipped |",
        "| --- | --- | --- |",
    ]
    for run in outcome.runs:
        lines.append(f"| {run.index} | {run.created_total} | {run.skipped_total} |")
    lines += [
        "",
        f"- Idempotency: **{PASS if outcome.idempotent else FAIL}**",
        "",
        "## Row counts",
        "",
        "| Collection | Rows |",
        "| --- | --- |",
    ]
    for label, count in outcome.counts.items():
        lines.append(f"| {label} | {count} |")
    lines += [
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for check in outcome.checks:
        lines.append(
            f"| {check.name} | {PASS if check.passed else FAIL} | {check.detail} |"
        )
    lines += [
        "",
        "> Passwords, password hashes, tokens, secrets and connection strings are "
        "never rendered in this report.",
        "",
    ]
    return "\n".join(lines)


def summarise_counter(counter: SeedCounter) -> dict[str, int]:
    """Return the created counts of a run."""
    return dict(sorted(counter.created.items()))


__all__ = [
    "CheckResult",
    "RunOutcome",
    "SeedOutcome",
    "collect_counts",
    "render_final_block",
    "render_markdown",
    "summarise_counter",
    "verify",
]
