"""Structural RLS coverage.

These assert the invariant from implementation_plan.md: every table that
carries a tenant column (``organization_id`` / ``school_id``) is either
protected by an ``AS PERMISSIVE`` policy bound ``TO app_user`` or explicitly
declared in ``RLS_EXEMPT_TABLES``. A future module that forgets to declare its
table fails CI here — not as a cross-tenant leak in production.
"""
from __future__ import annotations

from sqlalchemy import text

from app.db.rls import (
    ORG_SCOPED_TABLES,
    RLS_EXEMPT_TABLES,
    SCHOOL_SCOPED_TABLES,
    SELF_ORG_TABLES,
)

DECLARED = tuple({*ORG_SCOPED_TABLES, *SCHOOL_SCOPED_TABLES, *SELF_ORG_TABLES})


async def test_every_tenant_column_table_is_declared_or_exempt(app_session):
    tenant_tables = set(
        (
            await app_session.execute(
                text(
                    """
                    SELECT DISTINCT table_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name IN ('organization_id', 'school_id')
                    """
                )
            )
        )
        .scalars()
        .all()
    )
    unprotected = tenant_tables - set(DECLARED) - set(RLS_EXEMPT_TABLES)
    assert unprotected == set(), (
        f"tables with tenant columns missing RLS/exempt declaration: {sorted(unprotected)}"
    )


async def test_declared_tables_have_enforced_permissive_app_user_policy(app_session):
    for table in DECLARED:
        row = (
            await app_session.execute(
                text(
                    """
                    SELECT c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = :t
                    """
                ),
                {"t": table},
            )
        ).first()
        assert row is not None, f"{table}: table missing"
        assert row.relrowsecurity, f"{table}: RLS not enabled"
        assert row.relforcerowsecurity, f"{table}: FORCE RLS not set"

        policies = (
            await app_session.execute(
                text(
                    """
                    SELECT policyname, permissive, roles
                    FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = :t
                    """
                ),
                {"t": table},
            )
        ).all()
        matches = [p for p in policies if "tenant_isolation" in p.policyname]
        assert matches, f"{table}: tenant_isolation policy missing"
        for policy in matches:
            assert policy.permissive == "PERMISSIVE", f"{table}: policy not PERMISSIVE"
            assert "app_user" in policy.roles, f"{table}: policy not bound to app_user"


async def test_exempt_tables_carry_nullable_tenant_columns_and_no_policy(app_session):
    """Exemptions are deliberate and narrow: platform tables only."""
    for table in RLS_EXEMPT_TABLES:
        tenant_cols = set(
            (
                await app_session.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = :t
                          AND column_name IN ('organization_id', 'school_id')
                        """
                    ),
                    {"t": table},
                )
            )
            .scalars()
            .all()
        )
        assert tenant_cols, f"{table}: exempt table has no tenant column"
        policies = (
            await app_session.execute(
                text(
                    """
                    SELECT policyname FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = :t
                    """
                ),
                {"t": table},
            )
        ).scalars().all()
        assert not [p for p in policies if "tenant_isolation" in p], (
            f"{table}: exempt table unexpectedly has a tenant policy"
        )
