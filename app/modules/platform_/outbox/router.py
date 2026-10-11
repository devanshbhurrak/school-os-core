"""Outbox monitoring routes — platform-admin read-only (B4d System Health).

Surfaces dispatcher state for the admin System Health page:
* `GET /platform/outbox/summary` — counts per status (+ dead-lettered).
* `GET /platform/outbox` — recent events, newest first, filterable by status.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.authz import require
from app.core.context import RequestContext
from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.db.session import SessionDep
from app.modules.platform_.enums import OutboxStatus
from app.modules.platform_.models import OutboxEvent
from app.modules.platform_.outbox.permissions import P_OUTBOX_LIST
from app.modules.platform_.outbox.schemas import OutboxEventRead, OutboxStatusSummary

router = APIRouter(prefix="/platform/outbox", tags=["platform"])


@router.get("/summary", response_model=OutboxStatusSummary)
async def outbox_summary(
    ctx: RequestContext = Depends(require(P_OUTBOX_LIST)),
    session: SessionDep = None,
) -> OutboxStatusSummary:
    assert ctx.is_platform_admin or ctx.user_id  # guard is permission-based
    rows = (await session.execute(
        select(OutboxEvent.status, func.count())
        .group_by(OutboxEvent.status)
    )).all()
    counts = {status: int(n) for status, n in rows}
    dead = (await session.scalar(
        select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.status == OutboxStatus.FAILED.value,
            OutboxEvent.next_attempt_at.is_(None),
        )
    )) or 0
    return OutboxStatusSummary(
        pending=counts.get(OutboxStatus.PENDING.value, 0),
        processing=counts.get(OutboxStatus.PROCESSING.value, 0),
        sent=counts.get(OutboxStatus.SENT.value, 0),
        failed=counts.get(OutboxStatus.FAILED.value, 0),
        dead_lettered=int(dead),
    )


@router.get("", response_model=CursorPage[OutboxEventRead])
async def list_outbox_events(
    status: str | None = None,
    event_name: str | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_OUTBOX_LIST)),
    session: SessionDep = None,
) -> CursorPage[OutboxEventRead]:
    assert ctx.is_platform_admin or ctx.user_id
    stmt = select(OutboxEvent)
    if status:
        stmt = stmt.where(OutboxEvent.status == status)
    if event_name:
        stmt = stmt.where(OutboxEvent.event_name == event_name)
    page = await paginate_cursor(session, stmt, params, model=OutboxEvent)
    items = [OutboxEventRead.model_validate(e) for e in page.items]
    return CursorPage(items=items, next_cursor=page.next_cursor, has_more=page.has_more)
