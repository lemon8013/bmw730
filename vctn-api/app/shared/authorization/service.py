"""Authorization service - the single authority for every permission decision.

Controllers never evaluate a role, a department or a permission themselves; they
ask this service. Three gates are enforced, in order, for every administrative
action:

1. the API permission (``USER_EDIT``, ``ROLE_ASSIGN`` ...)
2. the field permission (``VISIBLE`` / ``HIDDEN`` / ``READ_ONLY`` / ``EDITABLE``)
3. the data scope (ALL / DEPARTMENT / DEPARTMENT_CHILDREN / SELF / CUSTOM)

Permissions are resolved from the database on every request, so a permission
change is effective immediately: no cached token carries a stale permission set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.departments.model import SysDepartment
from app.admin.permissions.model import SysPermission, SysPermissionField, SysRolePermission
from app.admin.roles.model import (
    SysRole,
    SysRoleDataScope,
    SysRoleInheritance,
    SysUserRole,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import DataScopeDeniedError, PermissionDeniedError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal

ACTIVE_STATUS: Final[str] = "ACTIVE"

SCOPE_ALL: Final[str] = "ALL"
SCOPE_DEPARTMENT: Final[str] = "DEPARTMENT"
SCOPE_DEPARTMENT_CHILDREN: Final[str] = "DEPARTMENT_CHILDREN"
SCOPE_SELF: Final[str] = "SELF"
SCOPE_CUSTOM: Final[str] = "CUSTOM"

FIELD_VISIBLE: Final[str] = "VISIBLE"
FIELD_HIDDEN: Final[str] = "HIDDEN"
FIELD_READ_ONLY: Final[str] = "READ_ONLY"
FIELD_EDITABLE: Final[str] = "EDITABLE"

_ROLE_TREE_SQL: Final[str] = """
WITH RECURSIVE role_tree AS (
    SELECT role_id FROM sys_user_role WHERE user_id = :user_id
    UNION
    SELECT parent_role_id
    FROM sys_role_inheritance
    JOIN role_tree ON sys_role_inheritance.child_role_id = role_tree.role_id
)
SELECT DISTINCT sys_permission.permission_code
FROM role_tree
JOIN sys_role_permission ON sys_role_permission.role_id = role_tree.role_id
JOIN sys_permission ON sys_permission.id = sys_role_permission.permission_id
WHERE sys_permission.status = :status
"""

_DEPARTMENT_TREE_SQL: Final[str] = """
WITH RECURSIVE department_tree AS (
    SELECT id FROM sys_department WHERE id = :department_id
    UNION
    SELECT sys_department.id
    FROM sys_department
    JOIN department_tree ON sys_department.parent_id = department_tree.id
)
SELECT id FROM department_tree
"""


@dataclass(frozen=True, slots=True)
class DataScope:
    """Resolved data scope of a caller."""

    all: bool = False
    department_ids: frozenset[int] = frozenset()
    self_only: bool = False

    def includes_department(self, department_id: int | None) -> bool:
        if self.all:
            return True
        if department_id is None:
            return False
        return department_id in self.department_ids

    def includes_owner(self, owner_id: int | None, *, caller_id: int) -> bool:
        if self.all:
            return True
        if owner_id is not None and owner_id == caller_id:
            return True
        return False


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """Result of an authorization check."""

    allowed: bool
    permission_code: str
    reason: str = ""
    field_modes: dict[str, str] = field(default_factory=dict)


class AuthorizationService:
    """The single authority for permission, field and data scope decisions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    async def permission_codes(self, session: AsyncSession, principal: Principal) -> frozenset[str]:
        """Return every permission code granted to the caller."""
        if not principal.is_admin:
            return frozenset()
        rows = (
            await session.execute(
                text(_ROLE_TREE_SQL), {"user_id": principal.subject_id, "status": ACTIVE_STATUS}
            )
        ).scalars()
        return frozenset(str(code) for code in rows)

    async def has_permission(
        self, session: AsyncSession, principal: Principal, permission_code: str
    ) -> bool:
        """Return whether the caller holds ``permission_code``."""
        if not principal.is_admin:
            return False
        if principal.is_super_admin:
            return True
        return permission_code in await self.permission_codes(session, principal)

    async def require_permission(
        self,
        session: AsyncSession,
        principal: Principal,
        permission_code: str,
        *,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        action: str | None = None,
    ) -> None:
        """Deny the request and audit the failure when permission is missing.

        Raises:
            PermissionDeniedError: when the caller lacks the permission.
        """
        if await self.has_permission(session, principal, permission_code):
            return
        await self._audit.record_failure(
            session,
            action=action or permission_code,
            error_code=str(PermissionDeniedError.code),
            operator_id=principal.subject_id,
            operator_username=principal.username,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        raise PermissionDeniedError(
            f"permission '{permission_code}' is required",
            data={"permission": permission_code},
        )

    # ------------------------------------------------------------------
    # Field permissions
    # ------------------------------------------------------------------
    async def field_modes(
        self, session: AsyncSession, principal: Principal, permission_code: str
    ) -> dict[str, str]:
        """Return the field policy attached to ``permission_code``."""
        if principal.is_super_admin:
            return {}
        rows = (
            await session.execute(
                select(SysPermissionField.field_code, SysPermissionField.field_mode)
                .join(SysPermission, SysPermission.id == SysPermissionField.permission_id)
                .where(SysPermission.permission_code == permission_code)
            )
        ).all()
        return {str(field_code): str(field_mode) for field_code, field_mode in rows}

    def apply_field_policy(self, payload: dict[str, Any], modes: dict[str, str]) -> dict[str, Any]:
        """Remove every field the caller is not allowed to see."""
        if not modes:
            return payload
        return {
            key: value
            for key, value in payload.items()
            if modes.get(key, FIELD_VISIBLE) != FIELD_HIDDEN
        }

    def assert_editable(
        self,
        payload: dict[str, Any],
        modes: dict[str, str],
        *,
        resource: str = "resource",
    ) -> None:
        """Reject changes to fields that are not editable for the caller."""
        for key in payload:
            mode = modes.get(key, FIELD_EDITABLE)
            if mode in (FIELD_HIDDEN, FIELD_READ_ONLY):
                raise PermissionDeniedError(
                    f"field '{key}' of {resource} is not editable",
                    data={"field": key, "mode": mode},
                )

    # ------------------------------------------------------------------
    # Data scope
    # ------------------------------------------------------------------
    async def data_scope(self, session: AsyncSession, principal: Principal) -> DataScope:
        """Resolve the data scope granted by every role of the caller."""
        if not principal.is_admin:
            return DataScope(self_only=True, department_ids=frozenset())
        if principal.is_super_admin:
            return DataScope(all=True)

        role_ids = (
            (
                await session.execute(
                    select(SysUserRole.role_id).where(SysUserRole.user_id == principal.subject_id)
                )
            )
            .scalars()
            .all()
        )
        inherited = await self._inherited_role_ids(session, [int(r) for r in role_ids])
        effective_role_ids = {int(r) for r in role_ids} | inherited
        if not effective_role_ids:
            return DataScope(self_only=True)

        roles = (
            await session.execute(
                select(SysRole.id, SysRole.data_scope).where(SysRole.id.in_(effective_role_ids))
            )
        ).all()

        department_ids: set[int] = set()
        scopes: set[str] = set()
        for _role_id, scope in roles:
            scopes.add(str(scope))
            if str(scope) == SCOPE_ALL:
                return DataScope(all=True)
            if str(scope) == SCOPE_DEPARTMENT and principal.department_id is not None:
                department_ids.add(int(principal.department_id))
            elif str(scope) == SCOPE_DEPARTMENT_CHILDREN and principal.department_id is not None:
                department_ids |= await self._department_tree(session, int(principal.department_id))

        if SCOPE_CUSTOM in scopes:
            custom = (
                await session.execute(
                    select(SysRoleDataScope.scope_type, SysRoleDataScope.department_id).where(
                        SysRoleDataScope.role_id.in_(effective_role_ids)
                    )
                )
            ).all()
            for scope_type, department_id in custom:
                if str(scope_type) == SCOPE_ALL:
                    return DataScope(all=True)
                if department_id is not None:
                    department_ids.add(int(department_id))

        self_only = bool(scopes) and scopes <= {SCOPE_SELF} and not department_ids
        return DataScope(all=False, department_ids=frozenset(department_ids), self_only=self_only)

    async def _inherited_role_ids(self, session: AsyncSession, role_ids: list[int]) -> set[int]:
        """Return every ancestor role reachable from ``role_ids``."""
        if not role_ids:
            return set()
        collected: set[int] = set()
        frontier = set(role_ids)
        while frontier:
            rows = (
                (
                    await session.execute(
                        select(SysRoleInheritance.parent_role_id).where(
                            SysRoleInheritance.child_role_id.in_(frontier)
                        )
                    )
                )
                .scalars()
                .all()
            )
            fresh = {int(r) for r in rows} - collected - set(role_ids)
            collected |= fresh
            frontier = fresh
            if not fresh:
                break
        return collected

    async def _department_tree(self, session: AsyncSession, department_id: int) -> set[int]:
        rows = (
            await session.execute(text(_DEPARTMENT_TREE_SQL), {"department_id": department_id})
        ).scalars()
        return {int(row) for row in rows}

    async def assert_manageable_user(
        self,
        session: AsyncSession,
        principal: Principal,
        *,
        target_user_id: int,
        target_department_id: int | None,
        target_is_super_admin: bool = False,
        action: str,
    ) -> DataScope:
        """Enforce data scope and the SUPER_ADMIN protection.

        Raises:
            PermissionDeniedError: when the target is a super administrator and
                the caller is not the same person.
            DataScopeDeniedError: when the target lies outside the data scope.
        """
        scope = await self.data_scope(session, principal)
        if target_is_super_admin and not principal.is_super_admin:
            await self._audit.record_failure(
                session,
                action=action,
                error_code=str(PermissionDeniedError.code),
                operator_id=principal.subject_id,
                operator_username=principal.username,
                resource_type="sys_user",
                resource_id=target_user_id,
                ip=principal.ip,
                user_agent=principal.user_agent,
            )
            raise PermissionDeniedError("super administrators can only be managed by themselves")

        if scope.includes_owner(target_user_id, caller_id=principal.subject_id):
            return scope
        if scope.includes_department(target_department_id):
            return scope

        await self._audit.record_failure(
            session,
            action=action,
            error_code=str(DataScopeDeniedError.code),
            operator_id=principal.subject_id,
            operator_username=principal.username,
            resource_type="sys_user",
            resource_id=target_user_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        raise DataScopeDeniedError("the target user is outside the manageable data scope")

    async def assert_department_manageable(
        self,
        session: AsyncSession,
        principal: Principal,
        *,
        department_id: int,
        action: str,
    ) -> None:
        """Raise when a department lies outside the caller's data scope."""
        scope = await self.data_scope(session, principal)
        if scope.all:
            return
        allowed = await self._department_tree(session, department_id)
        if not allowed.isdisjoint(scope.department_ids):
            return
        if department_id in scope.department_ids:
            return
        await self._audit.record_failure(
            session,
            action=action,
            error_code=str(DataScopeDeniedError.code),
            operator_id=principal.subject_id,
            operator_username=principal.username,
            resource_type="sys_department",
            resource_id=department_id,
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        raise DataScopeDeniedError("the target department is outside the manageable data scope")

    async def manageable_department_ids(
        self, session: AsyncSession, principal: Principal
    ) -> frozenset[int] | None:
        """Return the department ids a list query may return, or ``None`` for all."""
        scope = await self.data_scope(session, principal)
        if scope.all:
            return None
        return scope.department_ids

    # ------------------------------------------------------------------
    # Dynamic menus / routes
    # ------------------------------------------------------------------
    async def visible_resources(
        self, session: AsyncSession, principal: Principal, resource_types: tuple[str, ...]
    ) -> list[SysPermission]:
        """Return the menu / page / button resources the caller may see."""
        if not principal.is_admin:
            return []
        if principal.is_super_admin:
            result = await session.execute(
                select(SysPermission)
                .where(
                    SysPermission.status == ACTIVE_STATUS,
                    SysPermission.deleted_at.is_(None),
                    SysPermission.resource_type.in_(resource_types),
                )
                .order_by(SysPermission.sort_order, SysPermission.id)
            )
            return list(result.scalars())

        codes = await self.permission_codes(session, principal)
        if not codes:
            return []
        result = await session.execute(
            select(SysPermission)
            .where(
                SysPermission.status == ACTIVE_STATUS,
                SysPermission.deleted_at.is_(None),
                SysPermission.resource_type.in_(resource_types),
                SysPermission.permission_code.in_(codes),
            )
            .order_by(SysPermission.sort_order, SysPermission.id)
        )
        return list(result.scalars())

    async def department_options(self, session: AsyncSession) -> list[SysDepartment]:
        """Return every active department, used to build scope filters."""
        result = await session.execute(
            select(SysDepartment)
            .where(SysDepartment.deleted_at.is_(None))
            .order_by(SysDepartment.sort_order, SysDepartment.id)
        )
        return list(result.scalars())


__all__ = [
    "ACTIVE_STATUS",
    "AuthorizationDecision",
    "AuthorizationService",
    "DataScope",
    "DataScopeDeniedError",
    "FIELD_EDITABLE",
    "FIELD_HIDDEN",
    "FIELD_READ_ONLY",
    "FIELD_VISIBLE",
    "SCOPE_ALL",
    "SCOPE_CUSTOM",
    "SCOPE_DEPARTMENT",
    "SCOPE_DEPARTMENT_CHILDREN",
    "SCOPE_SELF",
    "SysRolePermission",
]
