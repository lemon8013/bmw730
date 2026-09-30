"""app.admin.users — business logic.

Every method enforces, in this order: the API permission (already checked by the
router dependency), the data scope, the field permission, then the change. Any
rejection is audited with ``result = FAILURE`` before the error is raised.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysPasswordHistory
from app.admin.auth.service import generate_temporary_password
from app.admin.users.model import SysUser
from app.admin.users.repository import AdminUserRepository
from app.admin.users.schema import (
    AssignRolesRequest,
    CreateUserRequest,
    MoveDepartmentRequest,
    OnlineUserResponse,
    RoleBrief,
    UpdateUserRequest,
    UserListQuery,
    UserResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.authorization.service import AuthorizationService
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.shared.security.password import hash_password, password_expiry_at, validate_password_policy

ACTIVE_STATUS: str = "ACTIVE"
DISABLED_STATUS: str = "DISABLED"


class AdminUserService:
    """Administrator account management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AdminUserRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._authorization = AuthorizationService(self._settings)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def list_users(
        self,
        actor: Principal,
        *,
        query: UserListQuery | None,
        page: PageParams,
    ) -> Page[UserResponse]:
        """Return one page of administrators limited by the caller's data scope."""
        scope_ids = await self._authorization.manageable_department_ids(self._session, actor)
        rows, total = await self._repository.search(
            keyword=query.keyword if query else None,
            department_id=int(query.department_id) if query and query.department_id else None,
            status=query.status if query else None,
            department_ids=None if scope_ids is None else list(scope_ids),
            limit=page.limit,
            offset=page.offset,
        )
        items = [await self._to_response(row) for row in rows]
        return Page.build(items=items, total=total, params=page)

    async def get_user(self, actor: Principal, user_id: int) -> UserResponse:
        """Return one administrator, enforcing the data scope."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="USER_VIEW")
        return await self._to_response(user)

    async def user_roles(self, actor: Principal, user_id: int) -> list[RoleBrief]:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="ROLE_VIEW")
        roles = await self._repository.roles_of(user_id)
        return [RoleBrief.model_validate(role) for role in roles]

    async def user_sessions(self, actor: Principal, user_id: int) -> list[dict[str, Any]]:
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="SESSION_VIEW")
        sessions = await self._repository.active_sessions_of(user_id)
        return [
            {
                "id": str(int(row.id)),
                "user_id": str(int(row.user_id)),
                "session_status": row.session_status,
                "ip": None if row.ip is None else str(row.ip),
                "device_type": row.device_type,
                "login_at": row.login_at,
                "last_active_at": row.last_active_at,
                "expires_at": row.expires_at,
                "revoked_at": row.revoked_at,
                "revoke_reason": row.revoke_reason,
            }
            for row in sessions
        ]

    async def online_users(self, actor: Principal) -> list[OnlineUserResponse]:
        """Return every administrator that currently holds an active session."""
        scope_ids = await self._authorization.manageable_department_ids(self._session, actor)
        pairs = await self._repository.online_sessions(
            department_ids=None if scope_ids is None else list(scope_ids)
        )
        return [
            OnlineUserResponse(
                user_id=str(int(user.id)),
                username=str(user.username),
                display_name=str(user.display_name),
                department_id=None if user.department_id is None else str(int(user.department_id)),
                session_id=str(int(session.id)),
                ip=None if session.ip is None else str(session.ip),
                device_type=session.device_type,
                login_at=session.login_at,
                last_active_at=session.last_active_at,
            )
            for user, session in pairs
        ]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    async def create_user(self, actor: Principal, payload: CreateUserRequest) -> UserResponse:
        """Create an administrator.

        A new account always starts with ``must_change_password`` set, and its
        department must sit inside the creator's data scope.
        """
        department_id = int(payload.department_id) if payload.department_id else None
        if department_id is not None:
            if not await self._repository.department_exists(department_id):
                raise NotFoundError("department not found")
            await self._authorization.assert_department_manageable(
                self._session, actor, department_id=department_id, action="USER_CREATE"
            )
        if await self._repository.exists_username(payload.username):
            raise ConflictError("username is already taken")

        role_ids = [int(value) for value in payload.role_ids]
        await self._assert_roles_assignable(actor, role_ids, action="USER_CREATE")

        temporary_password = payload.temporary_password or generate_temporary_password(
            self._settings
        )
        validate_password_policy(temporary_password, self._settings)
        now = datetime.datetime.now(datetime.UTC)

        user = SysUser(
            id=new_id(),
            username=payload.username,
            password_hash=hash_password(temporary_password),
            display_name=payload.display_name,
            email=payload.email,
            phone=payload.phone,
            department_id=department_id,
            status=ACTIVE_STATUS,
            is_super_admin=False,
            must_change_password=True,
            password_changed_at=now,
            password_expires_at=password_expiry_at(now, self._settings),
            failed_login_count=0,
        )
        self._repository.add(user)
        await self._session.flush()
        self._session.add(
            SysPasswordHistory(user_id=int(user.id), password_hash=str(user.password_hash))
        )
        await self._repository.replace_roles(int(user.id), role_ids)
        await self._session.flush()

        await self._audit.record(
            self._session,
            action="USER_CREATE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            after_data={
                "username": user.username,
                "department_id": department_id,
                "role_ids": role_ids,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="USER_CREATE",
            result=RESULT_SUCCESS,
            operator_id=actor.subject_id,
            resource_type="sys_user",
            resource_id=int(user.id),
        )
        await self._session.commit()
        response = await self._to_response(user)
        response.temporary_password = temporary_password
        return response

    async def update_user(
        self, actor: Principal, user_id: int, payload: UpdateUserRequest
    ) -> UserResponse:
        """Update an administrator, honouring the field permissions."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="USER_EDIT")

        modes = await self._authorization.field_modes(self._session, actor, "USER_EDIT")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        self._authorization.assert_editable(changes, modes, resource="sys_user")

        before = {
            "display_name": user.display_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "department_id": user.department_id,
        }
        for field_name, value in changes.items():
            if field_name == "department_id":
                target_department_id = int(value)
                if not await self._repository.department_exists(target_department_id):
                    raise NotFoundError("department not found")
                await self._authorization.assert_department_manageable(
                    self._session, actor, department_id=target_department_id, action="USER_EDIT"
                )
                setattr(user, field_name, target_department_id)
                continue
            if field_name == "status" and value not in (ACTIVE_STATUS, DISABLED_STATUS):
                raise ValidationError("status must be ACTIVE or DISABLED")
            setattr(user, field_name, value)
        user.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

        await self._audit.record(
            self._session,
            action="USER_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data=before,
            after_data={
                "display_name": user.display_name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status,
                "department_id": user.department_id,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(user)

    async def set_status(self, actor: Principal, user_id: int, *, active: bool) -> UserResponse:
        """Enable or disable an administrator."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="USER_EDIT")
        if user.is_super_admin and not actor.is_super_admin:
            raise BusinessRuleError("super administrators cannot be disabled")

        before = {"status": user.status}
        user.status = ACTIVE_STATUS if active else DISABLED_STATUS
        if not active:
            user.locked_until = None
        user.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="USER_ENABLE" if active else "USER_DISABLE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data=before,
            after_data={"status": user.status},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(user)

    async def delete_user(self, actor: Principal, user_id: int) -> None:
        """Logically delete an administrator and revoke its sessions."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="USER_DELETE")
        if user.is_super_admin:
            raise BusinessRuleError("super administrators cannot be deleted")

        now = datetime.datetime.now(datetime.UTC)
        user.deleted_at = now
        user.status = DISABLED_STATUS
        sessions = await self._repository.active_sessions_of(int(user.id))
        await self._repository.revoke_sessions(
            [int(row.id) for row in sessions], reason="USER_DELETED", revoked_at=now
        )
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="USER_DELETE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data={"status": "ACTIVE"},
            after_data={"deleted_at": now.isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()

    async def assign_roles(
        self, actor: Principal, user_id: int, payload: AssignRolesRequest
    ) -> list[RoleBrief]:
        """Replace the role set of an administrator, preventing escalation."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="ROLE_ASSIGN")
        if bool(user.is_super_admin) and not actor.is_super_admin:
            raise BusinessRuleError("the roles of a super administrator cannot be changed")

        role_ids = [int(value) for value in payload.role_ids]
        await self._assert_roles_assignable(actor, role_ids, action="ROLE_ASSIGN")

        before = await self._repository.role_ids_of(int(user.id))
        await self._repository.replace_roles(int(user.id), role_ids)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="ROLE_ASSIGN",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data={"role_ids": before},
            after_data={"role_ids": role_ids},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        roles = await self._repository.roles_of(int(user.id))
        return [RoleBrief.model_validate(role) for role in roles]

    async def move_department(
        self, actor: Principal, user_id: int, payload: MoveDepartmentRequest
    ) -> UserResponse:
        """Move an administrator into another department."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        await self._assert_manageable(actor, user, action="USER_EDIT")
        target = int(payload.department_id) if payload.department_id else None
        if target is not None:
            if not await self._repository.department_exists(target):
                raise NotFoundError("department not found")
            await self._authorization.assert_department_manageable(
                self._session, actor, department_id=target, action="USER_EDIT"
            )
        before = {"department_id": user.department_id}
        user.department_id = target
        user.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="USER_MOVE_DEPARTMENT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            before_data=before,
            after_data={"department_id": target},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return await self._to_response(user)

    async def force_logout(
        self, actor: Principal, user_id: int, *, reason: str | None = None
    ) -> dict[str, Any]:
        """Revoke every session of an administrator."""
        user = await self._repository.get(user_id)
        if user is None:
            raise NotFoundError("administrator not found")
        if bool(user.is_super_admin) and actor.subject_id != int(user.id):
            await self._audit.record_failure(
                self._session,
                action="SESSION_REVOKE",
                error_code="SUPER_ADMIN_PROTECTED",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_user",
                resource_id=int(user.id),
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("super administrators can only be forced out by themselves")

        await self._assert_manageable(actor, user, action="SESSION_REVOKE")
        sessions = await self._repository.active_sessions_of(int(user.id))
        revoked = await self._repository.revoke_sessions(
            [int(row.id) for row in sessions],
            reason=reason or "FORCED_LOGOUT",
            revoked_at=datetime.datetime.now(datetime.UTC),
        )
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="SESSION_REVOKE",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_user",
            resource_id=int(user.id),
            after_data={"revoked_sessions": revoked},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return {"user_id": str(int(user.id)), "revoked_sessions": revoked}

    async def batch_force_logout(
        self, actor: Principal, user_ids: list[int], *, reason: str | None = None
    ) -> dict[str, Any]:
        """Revoke the sessions of several administrators in one operation."""
        revoked_total = 0
        for user_id in user_ids:
            result = await self.force_logout(actor, user_id, reason=reason)
            revoked_total += int(result["revoked_sessions"])
        return {"revoked_sessions": revoked_total, "users": len(user_ids)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _assert_manageable(self, actor: Principal, user: SysUser, *, action: str) -> None:
        await self._authorization.assert_manageable_user(
            self._session,
            actor,
            target_user_id=int(user.id),
            target_department_id=user.department_id,
            target_is_super_admin=bool(user.is_super_admin),
            action=action,
        )

    async def _assert_roles_assignable(
        self, actor: Principal, role_ids: list[int], *, action: str
    ) -> None:
        """Reject a role grant that would escalate the caller's privileges."""
        if not role_ids:
            return
        roles = await self._repository.find_roles(role_ids)
        if len(roles) != len(set(role_ids)):
            await self._audit.record_failure(
                self._session,
                action=action,
                error_code="ROLE_NOT_FOUND",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_role",
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise NotFoundError("one or more roles do not exist")
        if actor.is_super_admin:
            return
        held = set(await self._repository.role_ids_of(actor.subject_id))
        escalations = sorted(set(role_ids) - held)
        if escalations:
            await self._audit.record_failure(
                self._session,
                action=action,
                error_code="ROLE_ESCALATION",
                operator_id=actor.subject_id,
                operator_username=actor.username,
                resource_type="sys_role",
                resource_id=",".join(str(value) for value in escalations),
                ip=actor.ip,
                user_agent=actor.user_agent,
            )
            await self._session.commit()
            raise BusinessRuleError("a role can only be granted when the operator holds it")

    async def _to_response(self, user: SysUser) -> UserResponse:
        roles = await self._repository.roles_of(int(user.id))
        return UserResponse(
            id=str(int(user.id)),
            username=str(user.username),
            display_name=str(user.display_name),
            email=user.email,
            phone=user.phone,
            department_id=None if user.department_id is None else str(int(user.department_id)),
            department_name=await self._repository.department_name(user.department_id),
            status=str(user.status),
            is_super_admin=bool(user.is_super_admin),
            must_change_password=bool(user.must_change_password),
            password_changed_at=user.password_changed_at,
            password_expires_at=user.password_expires_at,
            failed_login_count=int(user.failed_login_count or 0),
            locked_until=user.locked_until,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[RoleBrief.model_validate(role) for role in roles],
        )
