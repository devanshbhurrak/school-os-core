"""PostgreSQL Row-Level Security: the last line of tenant defence.

The repository layer already filters by tenant. RLS exists because that layer
is written by humans — a single forgotten `.where(organization_id == ...)` in a
future module is a cross-tenant data breach. With RLS enabled, that mistake
returns zero rows.

How it works
------------
`set_tenant_context` sets two *transaction-local* GUCs via `set_config(..., true)`:

    app.current_school_id       = '<ulid>' or ''
    app.current_organization_id = '<ulid>' or ''

`SET LOCAL` / `set_config` with `is_local=true` is transaction-scoped, so a
pooled connection cannot leak one request's tenant context into the next. The
`true` flag makes `current_setting` return NULL (not raise) when the variable
is unset; the policies coalesce that to `''`.

Every tenant-scoped table gets an `AS PERMISSIVE` policy bound `TO app_user`.
(PostgreSQL RLS semantics: a `RESTRICTIVE` policy can only narrow rows already
allowed by a permissive policy — with no permissive policy present, every row
is denied. So the tenant policy itself must be permissive.) `app_user` is a
NOLOGIN role; the application connects as `school_os_app`, a member that
inherits it. `FORCE ROW LEVEL SECURITY` applies the policy even to the table
owner, so the migration role (`app_migrator` / `school_os_migrator`, which has
BYPASSRLS) is the only escape hatch — and it never touches the app connection
string.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

GUC_SCHOOL_ID = "app.current_school_id"
GUC_ORG_ID = "app.current_organization_id"

POLICY_SUFFIX = "tenant_isolation"


async def set_tenant_context(
    session: AsyncSession,
    *,
    school_id: str | None = None,
    organization_id: str | None = None,
) -> None:
    """Bind the RLS context for the current transaction.

    Must run AFTER `session.begin()` (i.e. from within `get_db`'s yield).
    Values are parameterized and never interpolated.
    """
    await session.execute(
        text("SELECT set_config(:guc, :value, true)"),
        {"guc": GUC_SCHOOL_ID, "value": str(school_id) if school_id else ""},
    )
    await session.execute(
        text("SELECT set_config(:guc, :value, true)"),
        {"guc": GUC_ORG_ID, "value": str(organization_id) if organization_id else ""},
    )


def _school_ctx() -> str:
    return f"coalesce(current_setting('{GUC_SCHOOL_ID}', true), '')"


def _org_ctx() -> str:
    return f"coalesce(current_setting('{GUC_ORG_ID}', true), '')"


def _policy_statements(table: str, predicate: str) -> list[str]:
    policy = f"{table}_{POLICY_SUFFIX}"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;",
        f"DROP POLICY IF EXISTS {policy} ON {table};",
        f"CREATE POLICY {policy} ON {table} AS PERMISSIVE TO app_user "
        f"USING ({predicate}) WITH CHECK ({predicate});",
    ]


def school_scoped_policy_sql(table: str) -> list[str]:
    """For tables carrying a `school_id` column (future operational modules)."""
    ctx = _school_ctx()
    predicate = f"(school_id::text = {ctx} OR {ctx} = '')"
    return _policy_statements(table, predicate)


def org_scoped_policy_sql(table: str, *, allow_null_org: bool = False) -> list[str]:
    """For tables carrying a NOT NULL `organization_id` column."""
    ctx = _org_ctx()
    if allow_null_org:
        # System roles (organization_id IS NULL) are visible to everyone.
        predicate = f"(organization_id IS NULL OR organization_id::text = {ctx} OR {ctx} = '')"
    else:
        predicate = f"(organization_id::text = {ctx} OR {ctx} = '')"
    return _policy_statements(table, predicate)


def self_org_policy_sql(table: str) -> list[str]:
    """For the `organizations` root: the row's own id IS the tenant key."""
    ctx = _org_ctx()
    predicate = f"(id::text = {ctx} OR {ctx} = '')"
    return _policy_statements(table, predicate)


def drop_policy_sql(table: str) -> list[str]:
    policy = f"{table}_{POLICY_SUFFIX}"
    return [
        f"DROP POLICY IF EXISTS {policy} ON {table};",
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;",
    ]


# Tables protected by organization-level RLS. Every new org-scoped table MUST be
# added here in the same migration that creates it; tests/integration/
# test_rls_coverage.py fails CI if a tenant table is left unprotected.
ORG_SCOPED_TABLES: tuple[str, ...] = (
    "schools",
    "persons",
    "addresses",
    "contacts",
    "memberships",
    "roles",
)

# Tables protected by school-level RLS. Empty in Phase 1; future modules
# (students, attendance, ...) add their tables here with their policy.
SCHOOL_SCOPED_TABLES: tuple[str, ...] = (
    "academic_years",
    "academic_terms",
    "academic_classes",
    "subjects",
    "class_subjects",
    "cohorts",
)

# The organizations root is protected by a policy keyed on its own id.
SELF_ORG_TABLES: tuple[str, ...] = ("organizations",)

# Tables carrying a *nullable* tenant column. RLS would reject legitimate writes
# (a failed login has no school yet), so access is enforced at the API and
# repository layer only. This allowlist is asserted in test_rls_coverage.py;
# extending it requires deliberate review.
RLS_EXEMPT_TABLES: tuple[str, ...] = (
    "audit_logs",
    "outbox_events",
    "background_jobs",
    "feature_flags",
)
