"""Create the demo organization, its first school, and the platform admin.

Idempotent: skips anything that already exists. The admin user is created with
the password from `BOOTSTRAP_ADMIN_PASSWORD` (env), defaulting to
`Admin@ChangeMe1!`. A super-admin login account is created as a platform admin
(user.is_platform_admin = true).

Usage:  python -m scripts.bootstrap
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.hashing import hash_password  # noqa: E402
from app.modules.iam.enums import MembershipStatus, SchoolStatus, UserStatus  # noqa: E402

logger = structlog.get_logger(__name__)


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.modules.iam.models import Membership, Organization, Role, School, User

    settings = get_settings()
    admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "Admin@ChangeMe1!")

    engine = create_async_engine(settings.migration_database_url)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    async with session.begin():
        org = await session.scalar(
            select(Organization).where(Organization.code == settings.bootstrap_org_code)
        )
        if org is None:
            org = Organization(
                code=settings.bootstrap_org_code,
                name=settings.bootstrap_org_name,
                status="ACTIVE",
            )
            session.add(org)
            await session.flush()
            logger.info("organization_created", code=org.code)
        else:
            logger.info("organization_exists", code=org.code)

        school = await session.scalar(
            select(School).where(School.organization_id == org.id, School.code == settings.bootstrap_school_code)
        )
        if school is None:
            school = School(
                organization_id=org.id,
                code=settings.bootstrap_school_code,
                name=settings.bootstrap_school_name,
                status=SchoolStatus.ACTIVE.value,
            )
            session.add(school)
            await session.flush()
            logger.info("school_created", code=school.code)
        else:
            logger.info("school_exists", code=school.code)

        admin = await session.scalar(
            select(User).where(User.email == settings.bootstrap_admin_email)
        )
        if admin is None:
            admin = User(
                email=settings.bootstrap_admin_email,
                password_hash=hash_password(admin_password),
                status=UserStatus.ACTIVE.value,
                is_platform_admin=True,
                must_change_password=True,
            )
            session.add(admin)
            await session.flush()
            logger.info("admin_created", email=admin.email)
        else:
            admin.is_platform_admin = True
            logger.info("admin_exists", email=admin.email)

        super_admin_role = await session.scalar(
            select(Role).where(Role.code == "SUPER_ADMIN", Role.organization_id.is_(None))
        )
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == admin.id, Membership.organization_id == org.id
            )
        )
        if membership is None:
            membership = Membership(
                user_id=admin.id,
                organization_id=org.id,
                school_id=school.id,
                status=MembershipStatus.ACTIVE.value,
                is_default=True,
            )
            session.add(membership)
            await session.flush()
            logger.info("admin_membership_created")
        else:
            logger.info("admin_membership_exists")

        if super_admin_role is not None:
            from app.modules.iam.models import MembershipRole

            existing = await session.scalar(
                select(MembershipRole).where(
                    MembershipRole.membership_id == membership.id,
                    MembershipRole.role_id == super_admin_role.id,
                )
            )
            if existing is None:
                session.add(MembershipRole(membership_id=membership.id, role_id=super_admin_role.id))
                logger.info("super_admin_role_granted")
            else:
                logger.info("super_admin_role_exists")

    await session.close()
    await engine.dispose()
    logger.info(
        "bootstrap_complete",
        org=settings.bootstrap_org_code,
        school=settings.bootstrap_school_code,
        admin=settings.bootstrap_admin_email,
    )


if __name__ == "__main__":
    asyncio.run(main())
