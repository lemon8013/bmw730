"""Optional test data, seeded only with ``--mode=test``.

Test data is kept strictly separate from the production seed: a real deployment
runs ``--mode=system`` and never receives a test administrator, a test business
user or any fabricated content. The password for the test accounts is read from
the environment and never hard coded.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth.model import SysPasswordHistory
from app.admin.departments.model import SysDepartment
from app.admin.roles.model import SysRole, SysUserRole
from app.admin.users.model import SysUser
from app.core.config import Settings
from app.platform.users.model import (
    BizUser,
    BizUserLoginIdentity,
    BizUserPasswordHistory,
    BizUserProfile,
)
from app.scripts.seed.helpers import SeedCounter, ensure_row, find_one
from app.shared.ids import new_id
from app.shared.security.password import hash_password, password_expiry_at, validate_password_policy

TEST_ADMIN_USERNAME: str = "testadmin"
TEST_USER_USERNAME: str = "testuser"


async def seed_test_data(
    session: AsyncSession,
    settings: Settings,
    counter: SeedCounter,
    *,
    department: SysDepartment,
    roles: dict[str, SysRole],
    password: str,
) -> None:
    """Create the test administrator and one test business user."""
    validate_password_policy(password, settings)
    now = datetime.datetime.now(datetime.UTC)

    admin_password_hash = hash_password(password)
    existing_admin = await find_one(session, SysUser, username=TEST_ADMIN_USERNAME)
    if existing_admin is None:
        admin = SysUser(
            id=new_id(),
            username=TEST_ADMIN_USERNAME,
            password_hash=admin_password_hash,
            display_name="测试管理员",
            department_id=int(department.id),
            status="ACTIVE",
            is_super_admin=False,
            must_change_password=True,
            password_changed_at=now,
            password_expires_at=password_expiry_at(now, settings),
            failed_login_count=0,
        )
        session.add(admin)
        await session.flush()
        session.add(
            SysPasswordHistory(
                id=new_id(), user_id=int(admin.id), password_hash=admin_password_hash
            )
        )
        await session.flush()
        counter.created_one("test_admin")
    else:
        admin = existing_admin
        counter.skipped_one("test_admin")

    await ensure_row(
        session,
        SysUserRole,
        keys={"user_id": int(admin.id), "role_id": int(roles["DEPARTMENT_ADMIN"].id)},
        counter=counter,
        collection="test_user_roles",
    )

    user = await find_one(session, BizUser, username=TEST_USER_USERNAME)
    if user is None:
        user = BizUser(
            id=new_id(),
            username=TEST_USER_USERNAME,
            nickname="测试用户",
            status="ACTIVE",
            email="testuser@example.com",
            phone="13800000000",
            registered_at=now,
        )
        session.add(user)
        await session.flush()
        counter.created_one("test_biz_user")
    else:
        counter.skipped_one("test_biz_user")

    await ensure_row(
        session,
        BizUserProfile,
        keys={"user_id": int(user.id)},
        values={"gender": "UNKNOWN", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
        counter=counter,
        collection="test_biz_profiles",
    )

    user_password_hash = hash_password(password)
    await ensure_row(
        session,
        BizUserLoginIdentity,
        keys={"identity_type": "USERNAME", "identity_value": TEST_USER_USERNAME},
        values={"user_id": int(user.id), "verified": True},
        counter=counter,
        collection="test_biz_identities",
    )
    await ensure_row(
        session,
        BizUserPasswordHistory,
        keys={"user_id": int(user.id)},
        values={"password_hash": user_password_hash},
        counter=counter,
        collection="test_biz_password_history",
    )


__all__ = ["TEST_ADMIN_USERNAME", "TEST_USER_USERNAME", "seed_test_data"]
