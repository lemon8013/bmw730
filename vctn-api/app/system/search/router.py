"""app.system.search — HTTP endpoints.

Mounted by the application at the ``/system/search`` prefix. The search endpoint
is read-only and publicly usable (guests and authenticated users alike); it uses
``OptionalPrincipal`` so an anonymous caller is accepted.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import OptionalPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.system.search.schema import SearchResultItem
from app.system.search.service import SearchService

router = APIRouter(tags=["system:search"])


@router.get(
    "",
    response_model=ApiResponse[list[SearchResultItem]],
    summary="Unified site search",
)
async def search(
    session: DbSessionDep,
    q: str = Query(default="", max_length=128),
    type: str = Query(default="all"),
    _: OptionalPrincipal = None,
) -> ApiResponse[list[SearchResultItem]]:
    return success(await SearchService(session).search(q, type=type))
