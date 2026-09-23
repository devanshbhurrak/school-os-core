"""Integration test setup.

Strategy
--------
* A dedicated database (``school_os_test`` by default) is created if missing,
  migrated with ``alembic upgrade head``, and then populated with the
  code-declared system data (permissions + roles).
* The application engine always connects as ``school_os_app`` so RLS is
  enforced. Migrations, seeding and clean-up connect as ``school_os_migrator``
  (BYPASSRLS) so they can write regardless of tenant context.
* Every test starts from a clean slate: an autouse fixture truncates the
  public schema (except ``alembic_version``) and re-syncs system data.
* Rate limiters are in-process singletons, so they are cleared per test.

Environment
-----------
All app/migration URLs are forced to the test database *before* any ``app.*``
module is imported, because ``get_settings`` is cached at first use and env
vars take precedence over ``.env``. The superuser URL is used only to create
the database and grant schema privileges; it is never an application
connection.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# --- Environment must be set before any app.* import ----------------------
_TEST_DB = os.environ.get("SCHOOL_OS_TEST_DB", "school_os_test")
_TEST_HOST = os.environ.get("SCHOOL_OS_TEST_HOST", "localhost")
_TEST_PORT = os.environ.get("SCHOOL_OS_TEST_PORT", "5432")
_TEST_APP_ROLE = os.environ.get("SCHOOL_OS_TEST_APP_ROLE", "school_os_app")
_TEST_APP_PASSWORD = os.environ.get("SCHOOL_OS_TEST_APP_PASSWORD", "school_os_app_dev")
_TEST_MIGRATOR_ROLE = os.environ.get("SCHOOL_OS_TEST_MIGRATOR_ROLE", "school_os_migrator")
_TEST_MIGRATOR_PASSWORD = os.environ.get(
    "SCHOOL_OS_TEST_MIGRATOR_PASSWORD", "school_os_migrator_dev"
)

_APP_URL = (
    f"postgresql+asyncpg://{_TEST_APP_ROLE}:{_TEST_APP_PASSWORD}"
    f"@{_TEST_HOST}:{_TEST_PORT}/{_TEST_DB}"
)
_MIGRATOR_URL = (
    f"postgresql+asyncpg://{_TEST_MIGRATOR_ROLE}:{_TEST_MIGRATOR_PASSWORD}"
    f"@{_TEST_HOST}:{_TEST_PORT}/{_TEST_DB}"
)

os.environ["DATABASE_URL"] = _APP_URL
os.environ["MIGRATION_DATABASE_URL"] = _MIGRATOR_URL
os.environ["TEST_DATABASE_URL"] = _MIGRATOR_URL
os.environ["SYNC_DATABASE_URL"] = _MIGRATOR_URL
# Keep IP rate limiting out of the way so DB-level lockout / reset flows can
# be exercised directly (the limiter is still cleared per test).
os.environ.setdefault("LOGIN_RATE_LIMIT_PER_MINUTE", "1000")
os.environ.setdefault("PASSWORD_RESET_RATE_LIMIT_PER_HOUR", "1000")

# Only used to create the test database and grant schema privileges.
_SUPERUSER_URL = os.environ.get(
    "TEST_SUPERUSER_URL",
    "postgresql+asyncpg://postgres:root@localhost:5432/postgres",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

# Populate the permission registry (required by the sync_roles catalog).
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.hashing import hash_password  # noqa: E402
from app.core.permissions import registry  # noqa: E402
from app.core.ratelimit import login_limiter, password_reset_limiter  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402
from app.db.types import gen_ulid  # noqa: E402
from app.modules.academic.academic_classes import permissions as _acl_p  # noqa: E402, F401
from app.modules.academic.academic_terms import permissions as _at_p  # noqa: E402, F401
from app.modules.academic.academic_years import permissions as _ay_p  # noqa: E402, F401
from app.modules.academic.class_subjects import permissions as _cs_p  # noqa: E402, F401
from app.modules.academic.cohorts import permissions as _coh_p  # noqa: E402, F401
from app.modules.academic.subjects import permissions as _sub_p  # noqa: E402, F401
from app.modules.iam.memberships import permissions as _mp  # noqa: E402, F401
from app.modules.iam.models import (  # noqa: E402
    Membership,
    MembershipRole,
    Organization,
    Permission,
    Role,
    RolePermission,
    School,
    User,
)
from app.modules.iam.organizations import permissions as _op  # noqa: E402, F401
from app.modules.iam.roles import permissions as _rp  # noqa: E402, F401
from app.modules.iam.schools import permissions as _sp  # noqa: E402, F401
from app.modules.iam.users import permissions as _up  # noqa: E402, F401
from app.modules.people.addresses import permissions as _ap  # noqa: E402, F401
from app.modules.people.contacts import permissions as _cp  # noqa: E402, F401
from app.modules.people.persons import permissions as _pp  # noqa: E402, F401
from app.modules.platform_.audit import permissions as _audit_p  # noqa: E402, F401
from app.modules.students import permissions as _students_p  # noqa: E402, F401
from app.modules.students.enrollments import permissions as _enrollment_p  # noqa: E402, F401
from app.modules.students.guardians import permissions as _guardian_p  # noqa: E402, F401
from app.modules.teachers import permissions as _teachers_p  # noqa: E402, F401
from app.modules.timetables import permissions as _timetables_p  # noqa: E402, F401
from app.modules.announcements import permissions as _announcements_p  # noqa: E402, F401
from app.modules.attendance import permissions as _attendance_p  # noqa: E402, F401
from app.modules.bulk_import import permissions as _bulk_import_p  # noqa: E402, F401

# Imports the role catalog (and the permission modules it needs).
from scripts.sync_roles import ROLE_CATALOG  # noqa: E402

_migrator_engine = create_async_engine(
    _MIGRATOR_URL, poolclass=NullPool, pool_pre_ping=True
)
migrator_session_factory = async_sessionmaker(
    _migrator_engine, expire_on_commit=False, autoflush=False
)

# =========================================================================
# Seeded world
# =========================================================================

PASSWORD = "Str0ngTest!Pass2026"
PASSWORD_HASH = hash_password(PASSWORD)


@dataclass(frozen=True, slots=True)
class SeedUser:
    id: str
    email: str
    status: str = "ACTIVE"
    is_platform_admin: bool = False


@dataclass(frozen=True, slots=True)
class World:
    password: str
    org_a_id: str
    org_b_id: str
    school_a1_id: str
    school_a2_id: str
    school_b1_id: str
    school_b2_id: str
    platform_admin: SeedUser
    admin_a: SeedUser
    school_admin_a1: SeedUser
    teacher_a1: SeedUser
    parent_a1: SeedUser
    student_a1: SeedUser
    overlapping_teacher: SeedUser
    admin_b: SeedUser
    school_admin_b1: SeedUser
    suspended_user: SeedUser
    lone_user: SeedUser


def _make_world() -> World:
    return World(
        password=PASSWORD,
        org_a_id=gen_ulid(),
        org_b_id=gen_ulid(),
        school_a1_id=gen_ulid(),
        school_a2_id=gen_ulid(),
        school_b1_id=gen_ulid(),
        school_b2_id=gen_ulid(),
        platform_admin=SeedUser(id=gen_ulid(), email="platform@test.local", is_platform_admin=True),
        admin_a=SeedUser(id=gen_ulid(), email="admin.a@test.local"),
        school_admin_a1=SeedUser(id=gen_ulid(), email="school.admin.a1@test.local"),
        teacher_a1=SeedUser(id=gen_ulid(), email="teacher.a1@test.local"),
        parent_a1=SeedUser(id=gen_ulid(), email="parent.a1@test.local"),
        student_a1=SeedUser(id=gen_ulid(), email="student.a1@test.local"),
        overlapping_teacher=SeedUser(id=gen_ulid(), email="overlap.teacher@test.local"),
        admin_b=SeedUser(id=gen_ulid(), email="admin.b@test.local"),
        school_admin_b1=SeedUser(id=gen_ulid(), email="school.admin.b1@test.local"),
        suspended_user=SeedUser(id=gen_ulid(), email="suspended@test.local", status="SUSPENDED"),
        lone_user=SeedUser(id=gen_ulid(), email="lone@test.local"),
    )


WORLD = _make_world()


# =========================================================================
# Database setup / clean-up helpers
# =========================================================================


async def _ensure_database() -> None:
    import asyncpg
    from sqlalchemy.engine import make_url

    admin = make_url(_SUPERUSER_URL).set(drivername="postgresql")
    conn = await asyncpg.connect(dsn=admin.render_as_string(hide_password=False))
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB}"')
        # CREATE ON DATABASE lets the migrator run DDL (extensions, tables);
        # the app role only ever gets CONNECT + schema usage.
        await conn.execute(f'GRANT CREATE ON DATABASE "{_TEST_DB}" TO school_os_migrator')
        await conn.execute(f'GRANT CONNECT ON DATABASE "{_TEST_DB}" TO school_os_app')
    finally:
        await conn.close()

    test_admin = admin.set(database=_TEST_DB)
    conn = await asyncpg.connect(dsn=test_admin.render_as_string(hide_password=False))
    try:
        await conn.execute("GRANT CREATE, USAGE ON SCHEMA public TO school_os_migrator")
        await conn.execute("GRANT USAGE ON SCHEMA public TO school_os_app")
    finally:
        await conn.close()


def _run_alembic_upgrade() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_PROJECT_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed (rc={result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


async def _sync_system_data(session: AsyncSession) -> None:
    """Idempotently mirror the code-declared permissions and system roles."""
    declared = registry.all()
    existing = {row.code: row for row in (await session.scalars(select(Permission))).all()}
    for permission in declared:
        if permission.code not in existing:
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
    await session.flush()

    permission_ids = {
        row.code: row.id for row in (await session.scalars(select(Permission))).all()
    }
    for definition in ROLE_CATALOG:
        role = await session.scalar(
            select(Role)
            .options(
                selectinload(Role.permission_links).selectinload(RolePermission.permission)
            )
            .where(Role.code == definition["code"], Role.organization_id.is_(None))
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
            current = set()
            links: list[RolePermission] = []
        else:
            links = list(role.permission_links)
            current = {
                link.permission.code
                for link in links
                if link.permission and link.permission.code in permission_ids
            }

        desired = set(definition["permissions"])
        for link in links:
            if link.permission and link.permission.code not in desired:
                session.delete(link)
        for code in sorted(desired - current):
            session.add(
                RolePermission(id=gen_ulid(), role_id=role.id, permission_id=permission_ids[code])
            )
    await session.flush()


async def _truncate_all(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            DO $$
            DECLARE t text;
            BEGIN
                FOR t IN
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND tablename <> 'alembic_version'
                LOOP
                    EXECUTE format('TRUNCATE TABLE %I RESTART IDENTITY CASCADE', t);
                END LOOP;
            END $$;
            """
        )
    )


async def _insert_world(session: AsyncSession) -> None:
    w = WORLD
    session.add_all(
        [
            Organization(id=w.org_a_id, code="orga", name="Org A", status="ACTIVE"),
            Organization(id=w.org_b_id, code="orgb", name="Org B", status="ACTIVE"),
            School(
                id=w.school_a1_id,
                organization_id=w.org_a_id,
                code="sch-a1",
                name="School A1",
                status="ACTIVE",
            ),
            School(
                id=w.school_a2_id,
                organization_id=w.org_a_id,
                code="sch-a2",
                name="School A2",
                status="ACTIVE",
            ),
            School(
                id=w.school_b1_id,
                organization_id=w.org_b_id,
                code="sch-b1",
                name="School B1",
                status="ACTIVE",
            ),
            School(
                id=w.school_b2_id,
                organization_id=w.org_b_id,
                code="sch-b2",
                name="School B2",
                status="ACTIVE",
            ),
        ]
    )
    await session.flush()

    users = [
        w.platform_admin,
        w.admin_a,
        w.school_admin_a1,
        w.teacher_a1,
        w.parent_a1,
        w.student_a1,
        w.overlapping_teacher,
        w.admin_b,
        w.school_admin_b1,
        w.suspended_user,
        w.lone_user,
    ]
    for user in users:
        session.add(
            User(
                id=user.id,
                email=user.email,
                password_hash=PASSWORD_HASH,
                status=user.status,
                is_platform_admin=user.is_platform_admin,
            )
        )
    await session.flush()

    role_ids = {}
    for code in ("ORG_ADMIN", "SCHOOL_ADMIN", "TEACHER", "PARENT", "STUDENT"):
        role = await session.scalar(
            select(Role).where(Role.code == code, Role.organization_id.is_(None))
        )
        role_ids[code] = role.id

    async def grant(user_id: str, org_id: str, school_id: str, codes: tuple[str, ...]) -> None:
        membership = Membership(
            user_id=user_id,
            organization_id=org_id,
            school_id=school_id,
            status="ACTIVE",
        )
        session.add(membership)
        await session.flush()
        for code in codes:
            session.add(MembershipRole(membership_id=membership.id, role_id=role_ids[code]))

    await grant(w.admin_a.id, w.org_a_id, w.school_a1_id, ("ORG_ADMIN",))
    await grant(w.school_admin_a1.id, w.org_a_id, w.school_a1_id, ("SCHOOL_ADMIN",))
    await grant(w.teacher_a1.id, w.org_a_id, w.school_a1_id, ("TEACHER",))
    await grant(w.parent_a1.id, w.org_a_id, w.school_a1_id, ("PARENT",))
    await grant(w.student_a1.id, w.org_a_id, w.school_a1_id, ("STUDENT",))
    await grant(w.overlapping_teacher.id, w.org_a_id, w.school_a1_id, ("TEACHER",))
    await grant(w.overlapping_teacher.id, w.org_a_id, w.school_a2_id, ("TEACHER",))
    await grant(w.admin_b.id, w.org_b_id, w.school_b1_id, ("ORG_ADMIN",))
    await grant(w.school_admin_b1.id, w.org_b_id, w.school_b1_id, ("SCHOOL_ADMIN",))
    await grant(w.suspended_user.id, w.org_a_id, w.school_a1_id, ("STUDENT",))
    await session.flush()


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Create (if needed) + migrate the test database, once per session."""
    asyncio.run(_ensure_database())
    _run_alembic_upgrade()


@pytest.fixture
async def migrator_session() -> AsyncSession:
    """BYPASSRLS session for seeding / clean-up (no implicit transaction)."""
    async with migrator_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def _clean_db(migrated_database, migrator_session) -> None:
    """Reset the database and rate limiters before every test."""
    async with migrator_session.begin():
        await _truncate_all(migrator_session)
        await _sync_system_data(migrator_session)
    login_limiter._hits.clear()
    password_reset_limiter._hits.clear()
    yield
    # The app engine pools asyncpg connections tied to this test's event loop.
    # pytest-asyncio gives each test a fresh loop, so drop pooled connections to
    # avoid reusing ones bound to a closed loop.
    await _migrator_engine.dispose()
    from app.db.session import engine as app_engine

    await app_engine.dispose()


@pytest.fixture
async def seeded_world(migrator_session, _clean_db) -> World:
    """Fresh copy of the seed data (orgs, schools, users, memberships)."""
    async with migrator_session.begin():
        await _insert_world(migrator_session)
    return WORLD


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
async def client(app):
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def app_session() -> AsyncSession:
    """RLS-enforced session (school_os_app) already inside a transaction."""
    async with async_session_factory() as session, session.begin():
        yield session
