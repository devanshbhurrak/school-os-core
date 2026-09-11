"""Audit helper: write an audit row in the caller's transaction.

Audit is never a fire-and-forget. It happens in the same transaction as the
domain change, so either both commit or neither does (PRD §53, §31).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.modules.platform_.enums import AuditAction
from app.modules.platform_.models import AuditLog


async def audit(
    session: AsyncSession,
    ctx: RequestContext,
    action: str | AuditAction,
    entity_type: str,
    entity_id: str | None,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    summary: str | None = None,
    actor_label: str | None = None,
    organization_id: str | None = None,
    school_id: str | None = None,
) -> None:
    """Record an audit row. No commit — it is part of the caller's transaction."""
    actor_user_id = ctx.user_id if ctx.user_id else None
    log = AuditLog(
        organization_id=organization_id if organization_id is not None else ctx.organization_id,
        school_id=school_id if school_id is not None else ctx.school_id,
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        action=action.value if isinstance(action, AuditAction) else action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        before_snapshot=before,
        after_snapshot=after,
        request_id=ctx.request_id or None,
        ip_address=ctx.ip_address,
    )
    session.add(log)


def snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    """Capture the current values of `fields` from an ORM instance."""
    return {field: getattr(obj, field) for field in fields}
