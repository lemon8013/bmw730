"""app.admin.roles — data access."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.permissions.model import SysPermission, SysRolePermission
from app.admin.roles.model import SysRole, SysRoleDataScope, SysRoleInheritance, SysUserRole
from app.core.exceptions import ConflictError


class RoleRepository:
    """Data access for roles, their permissions and their inheritance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, role_id: int) -> SysRole | None:
        result = await self._session.execute(
            select(SysRole).where(SysRole.id == role_id, SysRole.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SysRole]:
        result = await self._session.execute(
            select(SysRole).where(SysRole.deleted_at.is_(None)).order_by(SysRole.id)
        )
        return list(result.scalars())

    async def exists_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        conditions = [func.lower(SysRole.role_code) == code.lower(), SysRole.deleted_at.is_(None)]
        if exclude_id is not None:
            conditions.append(SysRole.id != exclude_id)
        result = await self._session.execute(select(func.count(SysRole.id)).where(*conditions))
        return int(result.scalar_one()) > 0

    async def user_counts(self) -> dict[int, int]:
        result = await self._session.execute(
            select(SysUserRole.role_id, func.count(SysUserRole.user_id)).group_by(
                SysUserRole.role_id
            )
        )
        return {int(row[0]): int(row[1]) for row in result.all()}

    def add(self, role: SysRole) -> None:
        self._session.add(role)

    async def permissions_of(self, role_id: int) -> list[SysPermission]:
        result = await self._session.execute(
            select(SysPermission)
            .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
            .where(
                SysRolePermission.role_id == role_id,
                SysPermission.deleted_at.is_(None),
            )
            .order_by(SysPermission.sort_order, SysPermission.id)
        )
        return list(result.scalars())

    async def replace_permissions(self, role_id: int, permission_ids: Sequence[int]) -> None:
        from sqlalchemy import delete

        await self._session.execute(
            delete(SysRolePermission).where(SysRolePermission.role_id == role_id)
        )
        for permission_id in permission_ids:
            self._session.add(SysRolePermission(role_id=role_id, permission_id=permission_id))
        await self._session.flush()

    async def find_permissions(self, permission_ids: Sequence[int]) -> list[SysPermission]:
        if not permission_ids:
            return []
        result = await self._session.execute(
            select(SysPermission).where(
                SysPermission.id.in_(list(permission_ids)), SysPermission.deleted_at.is_(None)
            )
        )
        return list(result.scalars())

    async def parents_of(self, role_id: int) -> list[SysRole]:
        result = await self._session.execute(
            select(SysRole)
            .join(SysRoleInheritance, SysRoleInheritance.parent_role_id == SysRole.id)
            .where(SysRoleInheritance.child_role_id == role_id, SysRole.deleted_at.is_(None))
            .order_by(SysRole.id)
        )
        return list(result.scalars())

    async def replace_parents(self, role_id: int, parent_role_ids: Sequence[int]) -> None:
        from sqlalchemy import delete

        if role_id in set(parent_role_ids):
            raise ConflictError("a role cannot inherit from itself")
        await self._session.execute(
            delete(SysRoleInheritance).where(SysRoleInheritance.child_role_id == role_id)
        )
        for parent_role_id in parent_role_ids:
            self._session.add(
                SysRoleInheritance(parent_role_id=parent_role_id, child_role_id=role_id)
            )
        await self._session.flush()

    async def would_cycle(self, role_id: int, candidate_parent_ids: Sequence[int]) -> bool:
        """Return whether adding these parents closes an inheritance cycle."""
        rows = (
            await self._session.execute(
                select(SysRoleInheritance.parent_role_id, SysRoleInheritance.child_role_id)
            )
        ).all()
        children_of: dict[int, list[int]] = {}
        for parent_id, child_id in rows:
            children_of.setdefault(int(parent_id), []).append(int(child_id))
        for candidate in candidate_parent_ids:
            seen: set[int] = set()
            stack = [int(candidate)]
            while stack:
                current = stack.pop()
                if current == role_id:
                    return True
                if current in seen:
                    continue
                seen.add(current)
                stack.extend(children_of.get(current, []))
        return False

    async def data_scopes_of(self, role_id: int) -> list[SysRoleDataScope]:
        result = await self._session.execute(
            select(SysRoleDataScope).where(SysRoleDataScope.role_id == role_id)
        )
        return list(result.scalars())

    async def replace_data_scopes(
        self, role_id: int, entries: Sequence[tuple[str, int | None]]
    ) -> None:
        from sqlalchemy import delete

        await self._session.execute(
            delete(SysRoleDataScope).where(SysRoleDataScope.role_id == role_id)
        )
        for scope_type, department_id in entries:
            self._session.add(
                SysRoleDataScope(
                    role_id=role_id, scope_type=scope_type, department_id=department_id
                )
            )
        await self._session.flush()

    async def has_members(self, role_id: int) -> bool:
        result = await self._session.execute(
            select(func.count(SysUserRole.user_id)).where(SysUserRole.role_id == role_id)
        )
        return int(result.scalar_one()) > 0

    async def insert_guard(self, operation: str) -> None:
        """Translate a database uniqueness violation into a domain error."""
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"{operation} conflicts with an existing row") from exc
