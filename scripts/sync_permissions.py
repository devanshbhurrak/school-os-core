"""Sync the code-declared permission registry into the `permissions` table.

Runs as the migrator role (BYPASSRLS). Idempotent: inserts new codes, updates
changed descriptions, and removes codes no longer registered in code.

Usage:  python -m scripts.sync_permissions
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.permissions import registry  # noqa: E402
from app.modules import auth as _auth  # noqa: E402, F401  (register permissions)
from app.modules.iam.memberships import permissions as _membership_permissions  # noqa: E402, F401
from app.modules.iam.organizations import permissions as _org_permissions  # noqa: E402, F401
from app.modules.iam.roles import permissions as _role_permissions  # noqa: E402, F401
from app.modules.iam.schools import permissions as _school_permissions  # noqa: E402, F401
from app.modules.iam.users import permissions as _user_permissions  # noqa: E402, F401
from app.modules.people.addresses import permissions as _address_permissions  # noqa: E402, F401
from app.modules.people.contacts import permissions as _contact_permissions  # noqa: E402, F401
from app.modules.people.persons import permissions as _person_permissions  # noqa: E402, F401
from app.modules.platform_ import models as _platform_models  # noqa: E402, F401
from app.modules.platform_.audit import permissions as _audit_permissions  # noqa: E402, F401
from app.modules.platform_.audit import service as _audit_service  # noqa: E402, F401

logger = structlog.get_logger(__name__)


async def main() -> None:
    from sqlalchemy import delete, select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db.types import gen_ulid
    from app.modules.iam.models import Permission

    engine = create_async_engine(get_settings().migration_database_url)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    async with session.begin():
        await session.execute(text("SET ROLE school_os_migrator"))

        declared = registry.all()
        existing_rows = list((await session.scalars(select(Permission))).all())
        existing = {row.code: row for row in existing_rows}

        for permission in declared:
            row = existing.get(permission.code)
            if row is None:
                session.add(
                    Permission(
                        id=gen_ulid(),
                        code=permission.code,
                        module=permission.module,
                        resource=permission.resource,
                        action=permission.action,
                        description=permission.description,
                    )
                )
                logger.info("permission_added", code=permission.code)
            elif (
                row.module != permission.module
                or row.resource != permission.resource
                or row.action != permission.action
                or row.description != permission.description
            ):
                row.module = permission.module
                row.resource = permission.resource
                row.action = permission.action
                row.description = permission.description
                logger.info("permission_updated", code=permission.code)

        declared_codes = {p.code for p in declared}
        stale = [row for row in existing_rows if row.code not in declared_codes]
        for row in stale:
            await session.execute(delete(Permission).where(Permission.id == row.id))
            logger.info("permission_removed", code=row.code)
    await session.close()
    await engine.dispose()
    logger.info("sync_complete", total=len(declared), removed=len(stale))


if __name__ == "__main__":
    asyncio.run(main())
