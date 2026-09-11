"""Audit log data access — scoped to school (falling back to organization)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.platform_.models import AuditLog


async def get_by_id(
    session: AsyncSession,
    log_id: str,
    *,
    school_id: str | None = None,
    organization_id: str | None = None,
) -> AuditLog | None:
    stmt = select(AuditLog).where(AuditLog.id == log_id)
    if school_id:
        stmt = stmt.where(AuditLog.school_id == school_id)
    elif organization_id:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    return (await session.scalars(stmt)).first()


async def list_audit_logs(
    session: AsyncSession,
    params: CursorParams,
    *,
    school_id: str | None = None,
    organization_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> CursorPage[AuditLog]:
    stmt = select(AuditLog)
    if school_id:
        stmt = stmt.where(AuditLog.school_id == school_id)
    elif organization_id:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if created_from:
        stmt = stmt.where(AuditLog.created_at >= created_from)
    if created_to:
        stmt = stmt.where(AuditLog.created_at <= created_to)
    return await paginate_cursor(session, stmt, params, model=AuditLog)
