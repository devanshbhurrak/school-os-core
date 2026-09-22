"""Audit log routes — read-only, scoped to the request's school or organization.

No audit rows are ever created through the API: writes happen inside domain
transactions via `app.modules.platform_.audit.service.audit`.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.core.errors import NotFoundError
from app.core.pagination import CursorPage, CursorParams
from app.db.session import SessionDep
from app.modules.platform_.audit import repository
from app.modules.platform_.audit.permissions import P_AUDIT_LOG_LIST, P_AUDIT_LOG_READ
from app.modules.platform_.audit.schemas import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=CursorPage[AuditLogRead])
async def list_audit_logs(
    school_id: str | None = None,
    organization_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    params: CursorParams = Depends(),
    ctx: RequestContext = Depends(require(P_AUDIT_LOG_LIST)),
    session: SessionDep = None,
):
    # An explicit school outside the principal's reach is indistinguishable
    # from an empty result — no tenant information leaks.
    if school_id is not None and school_id not in ctx.accessible_school_ids:
        return CursorPage(items=[], next_cursor=None, has_more=False)

    effective_school_id = school_id if school_id is not None else ctx.school_id

    if effective_school_id:
        effective_org_id = None
    elif ctx.is_platform_admin and organization_id is not None:
        effective_org_id = organization_id
    else:
        effective_org_id = ctx.organization_id

    return await repository.list_audit_logs(
        session,
        params,
        school_id=effective_school_id,
        organization_id=effective_org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/{log_id}", response_model=AuditLogRead)
async def get_audit_log(
    log_id: str,
    ctx: RequestContext = Depends(require(P_AUDIT_LOG_READ)),
    session: SessionDep = None,
):
    school_id = ctx.school_id
    organization_id = None if school_id else ctx.organization_id
    if school_id is None and organization_id is None:
        raise NotFoundError(
            "The audit log was not found.", code="AUDIT_LOG_NOT_FOUND"
        )
    log = await repository.get_by_id(
        session, log_id, school_id=school_id, organization_id=organization_id
    )
    if log is None:
        raise NotFoundError(
            "The audit log was not found.", code="AUDIT_LOG_NOT_FOUND"
        )
    return log
