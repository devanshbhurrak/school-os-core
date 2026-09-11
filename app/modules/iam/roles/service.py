"""Role business logic."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    StaleResourceError,
)
from app.modules.iam.models import Permission, Role, RolePermission
from app.modules.iam.roles import repository
from app.modules.iam.roles.schemas import RoleCreate, RoleUpdate
from app.modules.platform_.audit.service import audit, snapshot

_SNAPSHOT_FIELDS = ["code", "name", "description", "scope_level", "data_scope", "is_system", "is_default"]


async def _fetch_permissions(session: AsyncSession, codes: list[str]) -> list[Permission]:
    stmt = select(Permission).where(Permission.code.in_(codes))
    rows = list((await session.scalars(stmt)).all())
    found = {p.code for p in rows}
    missing = set(codes) - found
    if missing:
        raise InvalidRequestError(
            "One or more permission codes are unknown.",
            code="UNKNOWN_PERMISSION_CODES",
            details={"codes": sorted(missing)},
        )
    return rows


def _permission_codes(role: Role) -> list[str]:
    return [link.permission.code for link in role.permission_links if link.permission]


async def create(session: AsyncSession, ctx: RequestContext, data: RoleCreate) -> Role:
    if ctx.organization_id is None:
        raise InvalidRequestError("No organization context is set for this request.")

    if await repository.get_by_code(session, ctx.organization_id, data.code):
        raise ConflictError(
            f"A role with code {data.code!r} already exists.",
            code="ROLE_CODE_TAKEN",
            details={"code": data.code},
        )

    permissions = await _fetch_permissions(session, data.permission_codes)
    role = Role(
        organization_id=ctx.organization_id,
        code=data.code,
        name=data.name,
        description=data.description,
        scope_level=data.scope_level.value,
        data_scope=data.data_scope.value,
        created_by_id=ctx.user_id,
    )
    session.add(role)
    await session.flush()
    for permission in permissions:
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.flush()

    await audit(
        session, ctx,
        action="ROLE_CREATED",
        entity_type="role",
        entity_id=role.id,
        summary=f"Role {role.code!r} created",
        after={**snapshot(role, _SNAPSHOT_FIELDS), "permissions": data.permission_codes},
    )
    return role


async def update(
    session: AsyncSession,
    ctx: RequestContext,
    role: Role,
    data: RoleUpdate,
) -> Role:
    if role.version != data.version:
        raise StaleResourceError()
    _assert_editable(role)

    payload = data.model_dump(exclude={"version", "permission_codes"}, exclude_none=True)
    permission_codes = data.permission_codes

    before = snapshot(role, _SNAPSHOT_FIELDS)
    for field, value in payload.items():
        setattr(role, field, value.value if hasattr(value, "value") else value)
    role.updated_by_id = ctx.user_id

    if permission_codes is not None:
        desired = {p.code for p in await _fetch_permissions(session, permission_codes)}
        current = {link.permission.code for link in role.permission_links if link.permission}
        for link in list(role.permission_links):
            if link.permission.code not in desired:
                await session.delete(link)
        for code in desired - current:
            permission = await session.scalar(select(Permission).where(Permission.code == code))
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.flush()

    await audit(
        session, ctx,
        action="ROLE_UPDATED",
        entity_type="role",
        entity_id=role.id,
        summary=f"Role {role.code!r} updated",
        before=before,
        after={**snapshot(role, _SNAPSHOT_FIELDS), "permissions": _permission_codes(role)},
    )
    return role


async def delete(session: AsyncSession, ctx: RequestContext, role: Role, version: int) -> None:
    if role.version != version:
        raise StaleResourceError()
    _assert_editable(role)

    before = snapshot(role, _SNAPSHOT_FIELDS)
    role.archived_at = datetime.now(UTC)
    role.updated_by_id = ctx.user_id
    await session.flush()

    await audit(
        session, ctx,
        action="ROLE_DELETED",
        entity_type="role",
        entity_id=role.id,
        summary=f"Role {role.code!r} deleted",
        before=before,
    )


def _assert_editable(role: Role) -> None:
    if role.is_system and role.organization_id is None:
        raise ForbiddenError("System roles cannot be modified.")


async def get_owned(session: AsyncSession, ctx: RequestContext, role_id: str) -> Role:
    if ctx.organization_id is None:
        role = await repository.get_by_id(session, role_id)
        if role is None or role.archived_at is not None:
            raise NotFoundError("The role was not found.", code="ROLE_NOT_FOUND")
        return role
    role = await repository.get_org_role(session, ctx.organization_id, role_id)
    if role is None:
        raise NotFoundError("The role was not found.", code="ROLE_NOT_FOUND")
    return role
