"""0006 — Convert tenant RLS policies from RESTRICTIVE to PERMISSIVE.

PostgreSQL semantics: a `RESTRICTIVE` policy can only narrow rows already
allowed by a permissive policy; a table protected by restrictive policies
alone (with no permissive policy) is fully invisible to the app role. The
original design (0002/0004) created only `AS RESTRICTIVE` policies, so every
RLS table read as empty. This migration drops and recreates the same
predicates as `AS PERMISSIVE`, restoring fail-open-tenant / tenant-scoped
behaviour (see app/db/rls.py).
"""
from __future__ import annotations

from alembic import op
from app.db.rls import (
    ORG_SCOPED_TABLES,
    SELF_ORG_TABLES,
    drop_policy_sql,
    org_scoped_policy_sql,
    self_org_policy_sql,
)

revision = "0006_permissive_rls"
down_revision = "0005_platform_tables"
branch_labels = None
depends_on = None

_RLS_SELF_ORG = list(SELF_ORG_TABLES)
_RLS_ORG = list(ORG_SCOPED_TABLES)


def upgrade() -> None:
    # Rebuild every tenant policy as PERMISSIVE.
    for table in [*_RLS_SELF_ORG, *_RLS_ORG]:
        for statement in drop_policy_sql(table):
            op.execute(statement)
    for table in _RLS_SELF_ORG:
        for statement in self_org_policy_sql(table):
            op.execute(statement)
    for table in _RLS_ORG:
        allow_null = table == "roles"
        for statement in org_scoped_policy_sql(table, allow_null_org=allow_null):
            op.execute(statement)


def downgrade() -> None:
    # Rebuild as RESTRICTIVE (the pre-0006 design). Restrictive-only policies
    # hide every row from app_user — reproduced exactly so the downgrade mirrors
    # the broken 0002/0004 state.
    for table in [*_RLS_SELF_ORG, *_RLS_ORG]:
        for statement in drop_policy_sql(table):
            op.execute(statement)
    for table in _RLS_SELF_ORG:
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "AS RESTRICTIVE TO app_user "
            "USING (TRUE) WITH CHECK (TRUE)"
        )
    for table in _RLS_ORG:
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "AS RESTRICTIVE TO app_user "
            "USING (TRUE) WITH CHECK (TRUE)"
        )
