"""app.platform.cosmetics — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.platform.cosmetics.model import BizUserEquipment
from app.platform.cosmetics.repository import (
    COSMETIC_SLOTS,
    SLOT_TYPE_BY_FIELD,
    CosmeticRepository,
)
from app.platform.cosmetics.schema import CosmeticResponse, UserCosmeticResponse
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal


class CosmeticService:
    """Ownership and equipment of cosmetics."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = CosmeticRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_cosmetics(self, user_id: int | None = None) -> list[CosmeticResponse]:
        """Return the cosmetic catalogue, flagged with what the caller owns."""
        rows = await self._repository.list_cosmetics()
        owned = await self._repository.owned_ids(user_id) if user_id is not None else set()
        return [
            CosmeticResponse(
                id=str(int(row.id)),
                cosmetic_code=str(row.cosmetic_code),
                cosmetic_name=str(row.cosmetic_name),
                cosmetic_type=str(row.cosmetic_type),
                asset_url=row.asset_url,
                metadata=row.metadata_payload,
                status=str(row.status),
                sort_order=int(row.sort_order or 0),
                owned=int(row.id) in owned,
            )
            for row in rows
        ]

    async def my_cosmetics(self, user_id: int) -> list[UserCosmeticResponse]:
        rows = await self._repository.owned(user_id)
        names: dict[int, tuple[str, str]] = {}
        for row in await self._repository.list_cosmetics():
            names[int(row.id)] = (str(row.cosmetic_name), str(row.cosmetic_type))
        return [
            UserCosmeticResponse(
                id=str(int(row.id)),
                user_id=str(int(row.user_id)),
                cosmetic_id=str(int(row.cosmetic_id)),
                cosmetic_name=names.get(int(row.cosmetic_id), (None, None))[0],
                cosmetic_type=names.get(int(row.cosmetic_id), (None, None))[1],
                obtained_at=row.obtained_at,
                source_type=row.source_type,
                source_id=row.source_id,
            )
            for row in rows
        ]

    async def equipment_row(self, user_id: int) -> BizUserEquipment:
        return await self._repository.equipment(user_id)

    async def equip(self, principal: Principal, **slots: int | None) -> BizUserEquipment:
        """Equip (or clear) cosmetic slots.

        A cosmetic can only be equipped when the caller owns it, it is active and
        its type matches the slot. Passing ``None`` clears the slot.
        """
        row = await self._repository.equipment(principal.subject_id)
        owned = await self._repository.owned_ids(principal.subject_id)
        for field, value in slots.items():
            if field not in COSMETIC_SLOTS:
                raise BusinessRuleError(f"'{field}' is not an equipment slot")
            if value is None:
                continue
            if value not in owned:
                raise BusinessRuleError("the cosmetic is not owned")
            cosmetic = await self._repository.get_cosmetic(value)
            if cosmetic is None:
                raise NotFoundError("cosmetic not found")
            if str(cosmetic.status) != "ACTIVE":
                raise BusinessRuleError("the cosmetic is not active")
            if str(cosmetic.cosmetic_type) != SLOT_TYPE_BY_FIELD[field]:
                raise BusinessRuleError(f"the cosmetic type does not match the slot '{field}'")
            setattr(row, field, value)
        for field, value in slots.items():
            if value is None and field in COSMETIC_SLOTS:
                setattr(row, field, None)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="COSMETIC_EQUIP",
            operator_id=principal.subject_id,
            resource_type="biz_user_equipment",
            resource_id=principal.subject_id,
            after_data={key: value for key, value in slots.items()},
            ip=principal.ip,
            user_agent=principal.user_agent,
        )
        await self._session.commit()
        return row

    async def grant(
        self,
        *,
        actor_id: int,
        actor_username: str,
        user_id: int,
        cosmetic_id: int,
        source_type: str = "ADMIN",
        source_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> UserCosmeticResponse:
        """Grant a cosmetic to a user (administrative action, audited)."""
        cosmetic = await self._repository.get_cosmetic(cosmetic_id)
        if cosmetic is None:
            raise NotFoundError("cosmetic not found")
        row = await self._repository.grant(
            user_id=user_id,
            cosmetic_id=cosmetic_id,
            source_type=source_type,
            source_id=source_id,
        )
        await self._audit.record(
            self._session,
            action="COSMETIC_GRANT",
            operator_id=actor_id,
            operator_username=actor_username,
            resource_type="biz_user_cosmetic",
            resource_id=int(row.id),
            after_data={
                "user_id": user_id,
                "cosmetic_id": cosmetic_id,
                "source_type": source_type,
            },
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
        return UserCosmeticResponse(
            id=str(int(row.id)),
            user_id=str(user_id),
            cosmetic_id=str(cosmetic_id),
            cosmetic_name=str(cosmetic.cosmetic_name),
            cosmetic_type=str(cosmetic.cosmetic_type),
            obtained_at=row.obtained_at,
            source_type=row.source_type,
            source_id=row.source_id,
        )

    async def revoke(
        self,
        *,
        actor_id: int,
        actor_username: str,
        user_id: int,
        cosmetic_id: int,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke a cosmetic and clear it from every equipment slot."""
        removed = await self._repository.revoke(user_id, cosmetic_id)
        if not removed:
            raise NotFoundError("the user does not own this cosmetic")
        await self._repository.unequip_slot(user_id, cosmetic_id)
        await self._audit.record(
            self._session,
            action="COSMETIC_REVOKE",
            operator_id=actor_id,
            operator_username=actor_username,
            resource_type="biz_user_cosmetic",
            resource_id=user_id,
            after_data={"cosmetic_id": cosmetic_id},
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
