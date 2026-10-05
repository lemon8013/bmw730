"""Dev helper: mint an admin access token without touching any password.

Creates a real session row for the admin principal, issues a token pair through
the project's own issuer, prints the access token, then rolls back so nothing
persists. Used only for local end-to-end probing.
"""
import asyncio
import datetime
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.admin.users.model import SysUser
from app.admin.auth.repository import AdminAuthRepository
from app.shared.database.engine import build_engine
from app.shared.database.session import build_session_factory
from app.shared.security.tokens import issue_token_pair


async def main(username: str = "admin") -> None:
    settings = get_settings()
    engine = build_engine(settings)
    factory = build_session_factory(engine)
    async with factory() as session:
        user = (
            await session.execute(select(SysUser).where(SysUser.username == username))
        ).scalars().first()
        if user is None:
            print("NO_USER", file=sys.stderr)
            raise SystemExit(1)
        now = datetime.datetime.now(datetime.UTC)
        repo = AdminAuthRepository(session)
        row = await repo.create_session(
            user_id=int(user.id),
            refresh_token_hash="",
            ip="127.0.0.1",
            user_agent="devtools",
            device_type="DESKTOP",
            login_at=now,
            expires_at=now + datetime.timedelta(seconds=settings.AUTH_REFRESH_TOKEN_TTL_SECONDS),
        )
        pair, _, _, _ = issue_token_pair(
            subject_id=int(user.id),
            session_id=int(row.id),
            subject_type="admin",
            now=now,
            settings=settings,
        )
        # The access check resolves the session row, so it must be committed.
        await session.commit()
        print(pair.access_token)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "admin"))
