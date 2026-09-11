"""Per-request context: who is acting and under which tenant scope.

`RequestContext` is the single object every route guard, repository filter and
audit row consumes. It is produced by `get_context` (below), which:

  1. Resolves the authenticated user (via `get_current_user_id`).
  2. Loads their active memberships and grants.
  3. Validates `X-School-ID` against those memberships — the header *selects*
     a school the caller already belongs to; it never *grants* access.
  4. Establishes the RLS transaction context (`SET LOCAL`).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import DataScope
from app.core.security import get_current_user_id
from app.db.session import get_db


def get_request_id(request: Request) -> str:
    """Return the request's correlation id, generating one on first use."""
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
    return request_id


def get_client_ip(request: Request) -> str | None:
    """Best-effort client IP honouring a trusted X-Forwarded-For header."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _client_ip(request: Request) -> str | None:
    return get_client_ip(request)


@dataclass(slots=True)
class RequestContext:
    user_id: str
    person_id: str | None
    email: str | None
    organization_id: str | None
    school_id: str | None
    accessible_school_ids: frozenset[str]
    permissions: frozenset[str]
    permission_scopes: dict[str, DataScope] = field(default_factory=dict)
    role_codes: frozenset[str] = frozenset()
    scope: DataScope | None = None
    request_id: str = ""
    ip_address: str | None = None
    is_platform_admin: bool = False

    def has_permission(self, code: str) -> bool:
        return self.is_platform_admin or code in self.permissions

    def effective_scope_for(self, code: str) -> DataScope | None:
        """Strongest scope under which this principal holds `code`, or None."""
        if self.is_platform_admin:
            return DataScope.PLATFORM
        return self.permission_scopes.get(code)


async def get_context(
    request: Request,
    school_id_header: Annotated[str | None, Header(alias="X-School-ID")] = None,
    user_id: Annotated[str, Depends(get_current_user_id)] = ...,
    session: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> RequestContext:
    """Resolve the authenticated principal and bind the RLS tenant context."""
    from app.db.rls import set_tenant_context
    from app.modules.iam.principal import resolve_principal

    principal = await resolve_principal(
        session,
        user_id=user_id,
        requested_school_id=school_id_header,
    )

    await set_tenant_context(
        session,
        school_id=principal.school_id,
        organization_id=principal.organization_id,
    )

    request_id = get_request_id(request)
    request.state.user_id = principal.user_id
    request.state.school_id = principal.school_id

    return RequestContext(
        user_id=principal.user_id,
        person_id=principal.person_id,
        email=principal.email,
        organization_id=principal.organization_id,
        school_id=principal.school_id,
        accessible_school_ids=principal.accessible_school_ids,
        permissions=principal.permissions,
        permission_scopes=principal.permission_scopes,
        role_codes=principal.role_codes,
        scope=principal.scope,
        request_id=request_id,
        ip_address=_client_ip(request),
        is_platform_admin=principal.is_platform_admin,
    )


async def get_public_context(request: Request) -> RequestContext:
    """Minimal context for public / unauthenticated endpoints (audit-safe)."""
    return RequestContext(
        user_id="",
        person_id=None,
        email=None,
        organization_id=None,
        school_id=None,
        accessible_school_ids=frozenset(),
        permissions=frozenset(),
        request_id=get_request_id(request),
        ip_address=_client_ip(request),
    )
