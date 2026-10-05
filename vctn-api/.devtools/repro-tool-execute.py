"""Reproduce the tools execute 500 outside HTTP to see the real traceback."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.tools.runtime.service import ToolRuntimeService  # noqa: E402


async def main() -> None:
    settings = get_settings()
    engine = (lambda s: None)(settings)  # placeholder to keep imports obvious
    del engine

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import app.platform.users.model  # noqa: F401 - registers biz_user on the metadata
    import app.tools.usage.model  # noqa: F401

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        service = ToolRuntimeService(session, settings=settings)
        try:
            response = await service.execute(
                231198665589395456,
                inputs={"input": '{"b":2,"a":1}', "mode": "pretty"},
                anonymous_id="repro-script",
                ip="127.0.0.1",
                user_agent="repro",
            )
            print("OK", response)
            await session.rollback()
        except Exception as exc:  # noqa: BLE001
            import traceback

            traceback.print_exc()
            await session.rollback()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
