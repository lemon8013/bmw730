"""app.tools.runtime — business logic.

Execution follows the frozen order:

    resolve subject
    -> risk (IP based abuse check)
    -> active version
    -> access policy
    -> quota
    -> rate limit
    -> concurrency
    -> runtime (provider looked up by component_key)
    -> usage
    -> behaviour analytics (through the outbox)

The runtime never writes an aggregate itself and never writes behaviour events:
usage goes through :class:`app.tools.usage.service.ToolUsageService` and the
analytics side reacts to the outbox event.
"""

from __future__ import annotations

import asyncio
import datetime
import time
from typing import Any, Final

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError, QuotaExceededError
from app.shared.ids import new_id
from app.shared.outbox.service import OutboxService
from app.shared.security.masking import mask_secret
from app.shared.tracing.context import get_trace_id
from app.system.jobs.model import SysJob
from app.system.risk.model import RiskRule
from app.tools.access.service import ToolAccessService
from app.tools.catalog.model import Tool
from app.tools.catalog.repository import ToolCatalogRepository
from app.tools.runtime.providers import (
    EXECUTION_MODE_ASYNC,
    EXECUTION_MODE_BACKEND,
    EXECUTION_MODE_FRONTEND,
    ToolError,
    ToolExecutionRequest,
    ToolExecutionResult,
    get_registry,
)
from app.tools.runtime.schema import ToolExecuteResponse
from app.tools.usage.service import ToolUsageService

MAX_INPUT_ITEMS: int = 50
MAX_INPUT_VALUE_CHARS: int = 100_000


class ToolRuntimeService:
    """Executes tools through the provider registry."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        redis: aioredis.Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._catalog = ToolCatalogRepository(session)
        self._access = ToolAccessService(session, redis=redis, settings=self._settings)
        self._usage = ToolUsageService(session, self._settings)
        self._outbox = OutboxService(self._settings)
        self._redis = redis

    async def access(self, tool_id: int, *, is_guest: bool, ip: str | None) -> Any:
        """Return the access decision for a caller."""
        return await self._access.resolve(tool_id, is_guest=is_guest, ip=ip)

    async def execute(
        self,
        tool_id: int,
        *,
        inputs: dict[str, Any],
        user_id: int | None = None,
        anonymous_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ToolExecuteResponse:
        """Execute a tool and record its usage."""
        started = time.perf_counter()
        tool = await self._load_tool(tool_id)
        version = await self._catalog.current_version(tool)
        component_key = str(tool.component_key)
        provider = get_registry().get(component_key)
        if provider is None:
            raise BusinessRuleError(f"no provider is registered for '{component_key}'")

        await self._enforce_risk(ip=ip, user_id=user_id)
        await self._access.enforce_quota(
            tool_id, is_guest=user_id is None, user_id=user_id, ip=ip
        )

        execution_mode = str(provider.execution_mode)
        if execution_mode == EXECUTION_MODE_ASYNC:
            job_id = await self._enqueue_job(tool, inputs, user_id=user_id)
            duration_ms = int((time.perf_counter() - started) * 1000)
            usage_event_id = await self._usage.record(
                tool_id=int(tool.id),
                tool_version_id=None if version is None else int(version.id),
                user_id=user_id,
                anonymous_id_hash=_hash_anonymous(anonymous_id),
                execution_mode=execution_mode,
                success=True,
                duration_ms=duration_ms,
            )
            await self._session.commit()
            return ToolExecuteResponse(
                tool_id=str(int(tool.id)),
                usage_event_id=str(usage_event_id),
                job_id=str(job_id),
                success=True,
                output={"status": "QUEUED"},
                duration_ms=duration_ms,
                execution_mode=execution_mode,
            )

        _validate_inputs(inputs)
        request = ToolExecutionRequest(
            component_key=component_key,
            inputs=inputs,
            runtime_config=dict(version.runtime_config or {}) if version is not None else {},
        )
        try:
            result = await asyncio.wait_for(
                provider.execute(request), timeout=_timeout_for(execution_mode, self._settings)
            )
        except ToolError as exc:
            result = ToolExecutionResult(False, None, exc.code, str(exc))
        except TimeoutError:
            result = ToolExecutionResult(False, None, "TOOL_TIMEOUT", "execution timed out")
        except Exception as exc:  # noqa: BLE001 - a provider bug must not break the API
            result = ToolExecutionResult(False, None, "TOOL_ERROR", type(exc).__name__)

        duration_ms = int((time.perf_counter() - started) * 1000)
        usage_event_id = await self._usage.record(
            tool_id=int(tool.id),
            tool_version_id=None if version is None else int(version.id),
            user_id=user_id,
            anonymous_id_hash=_hash_anonymous(anonymous_id),
            execution_mode=execution_mode,
            success=result.success,
            duration_ms=duration_ms,
        )
        await self._session.commit()
        return ToolExecuteResponse(
            tool_id=str(int(tool.id)),
            usage_event_id=str(usage_event_id),
            success=result.success,
            output=result.output,
            duration_ms=duration_ms,
            error_code=result.error_code,
            error_message=result.error_message,
            execution_mode=execution_mode,
        )

    async def _load_tool(self, tool_id: int) -> Tool:
        tool = await self._catalog.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("tool not found")
        if str(tool.status) != "ACTIVE":
            raise BusinessRuleError("the tool is not active")
        return tool

    async def _enqueue_job(
        self, tool: Tool, inputs: dict[str, Any], *, user_id: int | None
    ) -> int:
        """Create the asynchronous job that will run the tool later."""
        job = SysJob(
            id=new_id(),
            job_code=f"TOOL_EXECUTE:{tool.code}",
            job_name=f"Execute {tool.name}",
            job_type=JOB_TYPE_TOOL_EXECUTE,
            payload={
                "tool_id": int(tool.id),
                "component_key": str(tool.component_key),
                "inputs": inputs,
                "user_id": user_id,
            },
            status="PENDING",
            priority=0,
            attempt_count=0,
            max_attempts=self._settings.OUTBOX_MAX_ATTEMPTS,
            available_at=datetime.datetime.now(datetime.UTC),
            trace_id=get_trace_id(),
        )
        self._session.add(job)
        await self._session.flush()
        return int(job.id)

    async def _enforce_risk(self, *, ip: str | None, user_id: int | None) -> None:
        """Apply the enabled IP risk rules before spending quota."""
        if ip is None:
            return
        rows = (
            await self._session.execute(
                select(RiskRule).where(
                    RiskRule.enabled.is_(True), RiskRule.deleted_at.is_(None)
                )
            )
        ).scalars().all()
        for rule in rows:
            if str(rule.rule_type) != "IP":
                continue
            if self._redis is None:
                continue
            window = int(rule.window_seconds or 60)
            key = f"risk:ip:{ip}:{rule.rule_code}"
            count = int(await self._redis.incr(key))
            if count == 1:
                await self._redis.expire(key, window)
            if count > int(rule.threshold or 0) and str(rule.action) == "BLOCK":
                raise QuotaExceededError("the request was blocked by a risk rule")


JOB_TYPE_TOOL_EXECUTE: Final[str] = "TOOL_EXECUTE"


def _hash_anonymous(anonymous_id: str | None) -> str | None:
    import hashlib

    if not anonymous_id:
        return None
    return hashlib.sha256(anonymous_id.encode("utf-8")).hexdigest()


def _validate_inputs(inputs: dict[str, Any]) -> None:
    """Reject an oversized payload before it reaches any provider."""
    if len(inputs) > MAX_INPUT_ITEMS:
        raise BusinessRuleError(f"at most {MAX_INPUT_ITEMS} input fields are allowed")
    for key, value in inputs.items():
        if isinstance(value, str) and len(value) > MAX_INPUT_VALUE_CHARS:
            raise BusinessRuleError(f"the input '{key}' is too large")


def _timeout_for(execution_mode: str, settings: Settings) -> float:
    if execution_mode == EXECUTION_MODE_BACKEND:
        return float(settings.REDIS_SOCKET_TIMEOUT_SECONDS or 10)
    return float(settings.REDIS_SOCKET_TIMEOUT_SECONDS or 5)


def redact_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Return a log safe view of tool inputs (used by diagnostics)."""
    return {key: mask_secret(str(value)) for key, value in inputs.items()}


__all__ = [
    "EXECUTION_MODE_ASYNC",
    "EXECUTION_MODE_BACKEND",
    "EXECUTION_MODE_FRONTEND",
    "ToolRuntimeService",
]
