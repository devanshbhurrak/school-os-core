"""Resolves an authenticated user into a `Principal` for one request.

This is the single place where "who is this and what may they touch" is decided.
Everything downstream — route guards, repository filters, the RLS GUCs —
consumes its output. Keeping it in one function is what makes the tenant
isolation test suite meaningful: there is one code path to attack.

The active school is chosen as follows:
  1. If the caller sent `X-School-ID`, it must be among their active
     memberships. Otherwise 403 — the same 403 whether the school does not
     exist or the caller is simply not a member, so the header cannot be used
     to enumerate tenants.
  2. Otherwise, the caller's default membership.
  3. Otherwise, if they have exactly one, that one.
  4. Otherwise none, and school-scoped routes will reject the request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AccountInactiveError,
    AuthenticationError,
    TenantContextError,
)
from app.core.permissions import DataScope
from app.modules.iam.enums import MembershipStatus, SchoolStatus, UserStatus
from app.modules.iam.models import (
    Membership,
    MembershipRole,
    Role,
    RolePermission,
    School,
    User,
)


@dataclass(slots=True)
class Principal:
    user_id: str
    person_id: str | None
    email: str | None
    organization_id: str | None
    school_id: str | None
    accessible_school_ids: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    permission_scopes: dict[str, DataScope] = field(default_factory=dict)
    role_codes: frozenset[str] = frozenset()
    scope: DataScope | None = None
    is_platform_admin: bool = False


async def resolve_principal(
    session: AsyncSession,
    *,
    user_id: str,
    requested_school_id: str | None = None,
) -> Principal:
    user = await _load_user(session, user_id)

    if user.is_platform_admin:
        return await _platform_principal(session, user, requested_school_id)

    memberships = await _load_active_memberships(session, user_id)
    if not memberships:
        # Authenticated but attached to nothing: sign-in works, every tenant
        # route denies. This is an empty state, not an error.
        return Principal(
            user_id=user.id,
            person_id=user.person_id,
            email=user.email,
            organization_id=None,
            school_id=None,
        )

    organization_id = memberships[0].organization_id
    accessible = await _accessible_school_ids(session, memberships, organization_id)
    active_school_id = _select_active_school(memberships, accessible, requested_school_id)

    applicable = [
        m for m in memberships if m.school_id is None or m.school_id == active_school_id
    ]
    permissions, scopes, role_codes = _collect_grants(applicable)

    return Principal(
        user_id=user.id,
        person_id=user.person_id,
        email=user.email,
        organization_id=organization_id,
        school_id=active_school_id,
        accessible_school_ids=frozenset(accessible),
        permissions=frozenset(permissions),
        permission_scopes=scopes,
        role_codes=frozenset(role_codes),
        scope=DataScope.strongest(set(scopes.values())) if scopes else None,
        is_platform_admin=False,
    )


async def _load_user(session: AsyncSession, user_id: str) -> User:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AuthenticationError()
    if user.status != UserStatus.ACTIVE.value:
        raise AccountInactiveError()
    return user


async def _load_active_memberships(session: AsyncSession, user_id: str) -> list[Membership]:
    today = date.today()
    stmt = (
        select(Membership)
        .where(
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.ACTIVE.value,
        )
        .options(
            selectinload(Membership.role_links)
            .selectinload(MembershipRole.role)
            .selectinload(Role.permission_links)
            .selectinload(RolePermission.permission)
        )
    )
    rows = list((await session.scalars(stmt)).all())
    return [m for m in rows if _within_dates(m, today)]


def _within_dates(membership: Membership, today: date) -> bool:
    if membership.start_date and membership.start_date > today:
        return False
    return not (membership.end_date and membership.end_date < today)


async def _accessible_school_ids(
    session: AsyncSession,
    memberships: list[Membership],
    organization_id: str,
) -> set[str]:
    """Explicit school memberships, plus every school in the org when the user
    holds an org-level membership (school_id IS NULL)."""
    explicit = {m.school_id for m in memberships if m.school_id is not None}
    has_org_level = any(m.school_id is None for m in memberships)

    if has_org_level:
        stmt = (
            select(School.id)
            .where(
                School.organization_id == organization_id,
                School.deleted_at.is_(None),
                School.status.in_([SchoolStatus.ACTIVE.value, SchoolStatus.SETUP.value]),
            )
        )
        explicit |= set((await session.scalars(stmt)).all())
    return explicit


def _select_active_school(
    memberships: list[Membership],
    accessible: set[str],
    requested: str | None,
) -> str | None:
    if requested is not None:
        if requested not in accessible:
            raise TenantContextError()
        return requested

    default = next((m.school_id for m in memberships if m.is_default and m.school_id), None)
    if default is not None and default in accessible:
        return default
    if len(accessible) == 1:
        return next(iter(accessible))
    return None


def _collect_grants(
    memberships: list[Membership],
) -> tuple[set[str], dict[str, DataScope], set[str]]:
    now = datetime.now(UTC)
    permission_scopes: dict[str, DataScope] = {}
    role_codes: set[str] = set()

    for membership in memberships:
        for link in membership.role_links:
            if link.expires_at is not None and link.expires_at <= now:
                continue
            role = link.role
            if role is None or role.archived_at is not None:
                continue
            role_codes.add(role.code)
            grant_scope = DataScope(link.data_scope) if link.data_scope else DataScope(role.data_scope)

            for perm_link in role.permission_links:
                if perm_link.permission is None:
                    continue
                perm_scope = (
                    DataScope(perm_link.data_scope) if perm_link.data_scope else grant_scope
                )
                code = perm_link.permission.code
                existing = permission_scopes.get(code)
                if existing is None or perm_scope.strength() > existing.strength():
                    permission_scopes[code] = perm_scope

    return set(permission_scopes), permission_scopes, role_codes


async def _platform_principal(
    session: AsyncSession,
    user: User,
    requested_school_id: str | None,
) -> Principal:
    """Platform staff bypass tenancy but still get a concrete active school when
    they select one, so their actions are audited against it."""
    organization_id: str | None = None
    if requested_school_id is not None:
        school = await session.get(School, requested_school_id)
        if school is None or school.deleted_at is not None:
            raise TenantContextError()
        organization_id = school.organization_id

    return Principal(
        user_id=user.id,
        person_id=user.person_id,
        email=user.email,
        organization_id=organization_id,
        school_id=requested_school_id,
        role_codes=frozenset({"SUPER_ADMIN"}),
        scope=DataScope.PLATFORM,
        is_platform_admin=True,
    )
