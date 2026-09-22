"""Platform aggregate statistics — single query, platform-admin only."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.authz import require
from app.core.context import RequestContext
from app.db.session import SessionDep
from app.modules.iam.models import Organization, School, User
from app.modules.platform_.stats.permissions import P_PLATFORM_STATS_READ
from app.modules.platform_.stats.schemas import PlatformStats

router = APIRouter(prefix="/platform/stats", tags=["platform"])


@router.get("", response_model=PlatformStats)
async def get_platform_stats(
    ctx: RequestContext = Depends(require(P_PLATFORM_STATS_READ)),
    session: SessionDep = None,
) -> PlatformStats:
    """Return exact totals for the platform dashboard stat cards."""
    org_count = (await session.scalar(
        select(func.count()).select_from(Organization)
        .where(Organization.deleted_at.is_(None))
    )) or 0

    school_count = (await session.scalar(
        select(func.count()).select_from(School)
        .where(School.deleted_at.is_(None))
    )) or 0

    user_count = (await session.scalar(
        select(func.count()).select_from(User)
        .where(User.deleted_at.is_(None))
    )) or 0

    return PlatformStats(
        org_count=org_count,
        school_count=school_count,
        user_count=user_count,
    )
