"""Outbox helper: write an outbox row in the caller's transaction.

Phase 1 ships the table and this writer only — there is no dispatcher or
worker. The row is committed atomically with the domain change, so a future
worker never has to reconcile "attendance saved but notification missing".
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.modules.platform_.models import OutboxEvent


async def publish(
    session: AsyncSession,
    event_name: str,
    *,
    payload: dict[str, Any],
    ctx: RequestContext | None = None,
    organization_id: str | None = None,
    school_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    version: int = 1,
) -> None:
    """Enqueue an event. No commit — it is part of the caller's transaction."""
    event = OutboxEvent(
        event_name=event_name,
        event_version=version,
        payload=payload,
        organization_id=(
            organization_id if organization_id is not None else (ctx.organization_id if ctx else None)
        ),
        school_id=(
            school_id if school_id is not None else (ctx.school_id if ctx else None)
        ),
        actor_user_id=ctx.user_id if ctx and ctx.user_id else None,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=ctx.request_id if ctx else None,
    )
    session.add(event)
