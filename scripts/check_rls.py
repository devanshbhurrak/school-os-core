"""Operational audit: confirm every tenant table is RLS-protected.

The structural twin of tests/integration/test_rls_coverage.py, intended to be
run by an operator against a live database. Exits non-zero if any tenant table
is missing RLS or its policy.

Usage:  python -m scripts.check_rls
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.db.rls import (  # noqa: E402
    ORG_SCOPED_TABLES,
    RLS_EXEMPT_TABLES,
    SCHOOL_SCOPED_TABLES,
    SELF_ORG_TABLES,
)

TENANT_TABLES = (
    [*ORG_SCOPED_TABLES, *SELF_ORG_TABLES, *SCHOOL_SCOPED_TABLES]
)


async def main() -> int:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(get_settings().database_url)
    session = async_sessionmaker(engine)()

    failures: list[str] = []
    async with session.begin():
        rows = (await session.execute(text("""
            SELECT tablename,
                   relrowsecurity,
                   relforcerowsecurity
            FROM pg_catalog.pg_tables
            JOIN pg_catalog.pg_class ON relname = tablename
            WHERE schemaname = 'public'
        """))).all()
        by_table = {r.tablename: r for r in rows}

        for table in TENANT_TABLES:
            row = by_table.get(table)
            if row is None:
                failures.append(f"{table}: table missing")
                continue
            if not row.relrowsecurity:
                failures.append(f"{table}: RLS not enabled")
            if not row.relforcerowsecurity:
                failures.append(f"{table}: FORCE RLS not set")

            policies = (await session.execute(text(
                "SELECT policyname FROM pg_policies WHERE tablename = :t"
            ), {"t": table})).scalars().all()
            if not any("tenant_isolation" in p for p in policies):
                failures.append(f"{table}: tenant_isolation policy missing")

        # Every table carrying a tenant column must be covered by a policy or
        # be exempt. Tables without a tenant column (users, permissions,
        # role_permissions, refresh_tokens, ...) are not RLS candidates.
        tenant_column_tables = set(
            (
                await session.execute(text(
                    """
                    SELECT DISTINCT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name IN ('organization_id', 'school_id')
                    """
                ))
            )
            .scalars()
            .all()
        )
        unprotected = sorted(
            tenant_column_tables - set(TENANT_TABLES) - set(RLS_EXEMPT_TABLES)
        )
        for table in unprotected:
            failures.append(f"{table}: tenant table not declared in app/db/rls.py")

    await session.close()
    await engine.dispose()

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"\n{len(failures)} RLS problem(s) found.")
        return 1

    print(f"OK: {len(TENANT_TABLES)} tenant tables protected by RLS.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
