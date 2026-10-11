"""Feature flag routes — read-only list for the admin System Health page (B4d).

Flag evaluation middleware lands in a later phase; Phase 3 only needs
visibility into configured flags.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.db.session import SessionDep
from app.modules.platform_.feature_flags.permissions import P_FEATURE_FLAG_LIST
from app.modules.platform_.feature_flags.schemas import FeatureFlagRead
from app.modules.platform_.models import FeatureFlag

router = APIRouter(prefix="/platform/feature-flags", tags=["platform"])


@router.get("", response_model=CursorPage[FeatureFlagRead])
async def list_feature_flags(
    enabled: bool | None = None,
    key: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_FEATURE_FLAG_LIST)),
    session: SessionDep = None,
) -> CursorPage[FeatureFlagRead]:
    assert ctx.is_platform_admin or ctx.user_id
    stmt = select(FeatureFlag)
    if enabled is not None:
        stmt = stmt.where(FeatureFlag.enabled == enabled)
    if key:
        stmt = stmt.where(FeatureFlag.key == key)
    page = await paginate_cursor(session, stmt, params, model=FeatureFlag)
    items = [FeatureFlagRead.model_validate(f) for f in page.items]
    return CursorPage(items=items, next_cursor=page.next_cursor, has_more=page.has_more)
