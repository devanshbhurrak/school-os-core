"""Seed / refresh the immutable system roles.

System roles have `organization_id NULL` and `is_system = true`. Tenants cannot
edit them, so upgrades can add permissions here without merging per-tenant edits.
The role catalog below declares codes as explicit lists (all checked against the
registry at import time — a typo crashes, never silently 403s).

Usage:  python -m scripts.sync_roles
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog  # noqa: E402

from app.core.permissions import DataScope, registry  # noqa: E402
from app.modules import auth as _auth  # noqa: E402, F401
from app.modules.academic.academic_classes import permissions as _acl_p  # noqa: E402, F401
from app.modules.academic.academic_terms import permissions as _at_p  # noqa: E402, F401
from app.modules.academic.academic_years import permissions as _ay_p  # noqa: E402, F401
from app.modules.academic.class_subjects import permissions as _cs_p  # noqa: E402, F401
from app.modules.academic.cohorts import permissions as _coh_p  # noqa: E402, F401
from app.modules.academic.subjects import permissions as _sub_p  # noqa: E402, F401
from app.modules.iam.memberships import permissions as _mp  # noqa: E402, F401
from app.modules.iam.organizations import permissions as _op  # noqa: E402, F401
from app.modules.iam.roles import permissions as _rp  # noqa: E402, F401
from app.modules.iam.schools import permissions as _sp  # noqa: E402, F401
from app.modules.iam.users import permissions as _up  # noqa: E402, F401
from app.modules.people.addresses import permissions as _ap  # noqa: E402, F401
from app.modules.people.contacts import permissions as _cp  # noqa: E402, F401
from app.modules.people.persons import permissions as _pp  # noqa: E402, F401
from app.modules.platform_.audit import permissions as _audit_p  # noqa: E402, F401

logger = structlog.get_logger(__name__)


def all_in_module(module: str) -> list[str]:
    return sorted(p.code for p in registry.all() if p.module == module)


def all_permissions() -> list[str]:
    return sorted(p.code for p in registry.all())


ROLE_CATALOG: list[dict] = [
    {
        "code": "SUPER_ADMIN",
        "name": "Platform Super Admin",
        "description": "Platform staff. Full access across all tenants.",
        "scope_level": "PLATFORM",
        "data_scope": DataScope.PLATFORM.value,
        "permissions": all_permissions(),
    },
    {
        "code": "ORG_ADMIN",
        "name": "Organization Administrator",
        "description": "Runs the whole organization: schools, users, roles.",
        "scope_level": "ORGANIZATION",
        "data_scope": DataScope.ORGANIZATION.value,
        "permissions": all_in_module("iam") + all_in_module("people") + all_in_module("academic")
        + all_in_module("platform"),
    },
    {
        "code": "SCHOOL_ADMIN",
        "name": "School Administrator",
        "description": "Operates one school: people and contacts.",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.SCHOOL.value,
        "permissions": all_in_module("people")
        + all_in_module("academic")
        + [c for c in all_in_module("iam") if c.startswith("iam.membership.")
           or c.startswith("iam.user.") or c.startswith("iam.school.") or c.startswith("iam.role.")]
        + all_in_module("platform"),
    },
    {
        "code": "PRINCIPAL",
        "name": "Principal",
        "description": "Reads all school data, manages people.",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.SCHOOL.value,
        "permissions": [c for c in all_in_module("people") if c.endswith(".read") or c.endswith(".list")]
        + [c for c in all_in_module("people") if c.endswith(".create") or c.endswith(".update")],
    },
    {
        "code": "TEACHER",
        "name": "Teacher",
        "description": "Sees assigned students (Phase 1: reads people).",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.ASSIGNED.value,
        "permissions": [c for c in all_in_module("people") if c.endswith(".read") or c.endswith(".list")],
    },
    {
        "code": "STAFF",
        "name": "Staff",
        "description": "Non-teaching staff. Read-only people access.",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.SCHOOL.value,
        "permissions": [c for c in all_in_module("people") if c.endswith(".read") or c.endswith(".list")],
    },
    {
        "code": "PARENT",
        "name": "Parent / Guardian",
        "description": "Reads only their own children (Phase 1: own person record).",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.OWN.value,
        "permissions": [c for c in all_in_module("people") if c.endswith(".read") or c.endswith(".list")],
    },
    {
        "code": "STUDENT",
        "name": "Student",
        "description": "Reads only their own record.",
        "scope_level": "SCHOOL",
        "data_scope": DataScope.OWN.value,
        "permissions": [c for c in all_in_module("people") if c.endswith(".read")],
    },
]


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.db.types import gen_ulid
    from app.modules.iam.models import Permission, Role, RolePermission

    # Validate catalog at import time.
    for definition in ROLE_CATALOG:
        for code in definition["permissions"]:
            registry.require_registered(code)

    engine = create_async_engine(get_settings().migration_database_url)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    async with session.begin():
        permission_rows = {
            row.code: row for row in (await session.scalars(select(Permission))).all()
        }

        for definition in ROLE_CATALOG:
            role = await session.scalar(
                select(Role).where(
                    Role.code == definition["code"],
                    Role.organization_id.is_(None),
                    Role.deleted_at.is_(None),
                )
            )
            if role is None:
                role = Role(
                    id=gen_ulid(),
                    organization_id=None,
                    code=definition["code"],
                    name=definition["name"],
                    description=definition["description"],
                    scope_level=definition["scope_level"],
                    data_scope=definition["data_scope"],
                    is_system=True,
                )
                session.add(role)
                await session.flush()
                await session.refresh(role, attribute_names=["permission_links"])
                logger.info("role_created", code=definition["code"])
            else:
                role.name = definition["name"]
                role.description = definition["description"]
                role.scope_level = definition["scope_level"]
                role.data_scope = definition["data_scope"]

            desired = set(definition["permissions"])
            current = {
                link.permission.code
                for link in role.permission_links
                if link.permission and link.permission.code in permission_rows
            }
            for link in list(role.permission_links):
                if link.permission.code not in desired:
                    await session.delete(link)
            for code in sorted(desired - current):
                session.add(
                    RolePermission(
                        id=gen_ulid(),
                        role_id=role.id,
                        permission_id=permission_rows[code].id,
                    )
                )
                logger.info("permission_granted", role=definition["code"], permission=code)

    await session.close()
    await engine.dispose()
    logger.info("sync_roles_complete", roles=len(ROLE_CATALOG))


if __name__ == "__main__":
    asyncio.run(main())
