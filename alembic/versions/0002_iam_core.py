"""0002 — IAM core: organizations, schools, users, memberships, roles.

Row-Level Security is enabled on every tenant-scoped table in the same
migration that creates it — a table can never exist unprotected. This is
enforced structurally by tests/integration/test_rls_coverage.py.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import (
    ORG_SCOPED_TABLES,
    SELF_ORG_TABLES,
    drop_policy_sql,
    org_scoped_policy_sql,
    self_org_policy_sql,
)

revision = "0002_iam_core"
down_revision = "0001_db_roles_and_rls_setup"
branch_labels = None
depends_on = None

# Tables created in this migration (for the downgrade).
_CREATED = ["organizations", "schools", "users", "permissions", "roles", "role_permissions", "memberships", "membership_roles"]
_RLS_ORG = [t for t in ORG_SCOPED_TABLES if t in _CREATED]
_RLS_SELF_ORG = [t for t in SELF_ORG_TABLES if t in _CREATED]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=250), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="TRIAL", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("locale", sa.String(length=16), server_default="en-IN", nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=24), nullable=True),
        sa.Column("plan_code", sa.String(length=40), server_default="foundation", nullable=False),
        sa.Column("entitlements", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("parent_organization_id", sa.String(length=26), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('TRIAL', 'ACTIVE', 'SUSPENDED', 'CLOSED')", name=op.f("ck_organizations_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("code", name="uq_organizations_code"),
    )
    op.create_index(op.f("ix_organizations_status"), "organizations", ["status"], unique=False)

    op.create_table(
        "schools",
        sa.Column("organization_id", sa.String(length=26), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="SETUP", nullable=False),
        sa.Column("parent_school_id", sa.String(length=26), nullable=True),
        sa.Column("hierarchy_path", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("locale", sa.String(length=16), server_default="en-IN", nullable=False),
        sa.Column("board", sa.String(length=40), nullable=True),
        sa.Column("affiliation_number", sa.String(length=60), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=24), nullable=True),
        sa.Column("address_id", sa.String(length=26), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('SETUP', 'ACTIVE', 'SUSPENDED', 'CLOSED')", name=op.f("ck_schools_status")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_schools_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_school_id"], ["schools.id"], name=op.f("fk_schools_parent_school_id_schools"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schools")),
        sa.UniqueConstraint("organization_id", "code", name="uq_schools_organization_id_code"),
    )
    op.create_index(op.f("ix_schools_organization_id"), "schools", ["organization_id"], unique=False)
    op.create_index(op.f("ix_schools_status"), "schools", ["status"], unique=False)

    op.create_table(
        "users",
        sa.Column("person_id", sa.String(length=26), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone", sa.String(length=24), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="INVITED", nullable=False),
        sa.Column("is_platform_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permissions_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('INVITED', 'ACTIVE', 'SUSPENDED', 'DISABLED')", name=op.f("ck_users_status")),
        sa.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name=op.f("ck_users_contact_present")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("resource", sa.String(length=60), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("platform_only", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index(op.f("ix_permissions_module"), "permissions", ["module"], unique=False)

    op.create_table(
        "roles",
        sa.Column("organization_id", sa.String(length=26), nullable=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=True),
        sa.Column("scope_level", sa.String(length=20), server_default="SCHOOL", nullable=False),
        sa.Column("data_scope", sa.String(length=20), server_default="SCHOOL", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(length=26), nullable=True),
        sa.Column("updated_by_id", sa.String(length=26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("data_scope IN ('OWN', 'ASSIGNED', 'SCHOOL', 'ORGANIZATION', 'PLATFORM')", name=op.f("ck_roles_data_scope")),
        sa.CheckConstraint("scope_level IN ('PLATFORM', 'ORGANIZATION', 'SCHOOL')", name=op.f("ck_roles_scope_level")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_roles_organization_id_organizations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("organization_id", "code", name="uq_roles_organization_id_code", postgresql_nulls_not_distinct=True),
    )
    op.create_index(op.f("ix_roles_organization_id"), "roles", ["organization_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=26), nullable=False),
        sa.Column("permission_id", sa.String(length=26), nullable=False),
        sa.Column("data_scope", sa.String(length=20), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], name=op.f("fk_role_permissions_permission_id_permissions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name=op.f("fk_role_permissions_role_id_roles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_permissions")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_id_permission_id"),
    )
    op.create_index(op.f("ix_role_permissions_permission_id"), "role_permissions", ["permission_id"], unique=False)
    op.create_index(op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("user_id", sa.String(length=26), nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=False),
        sa.Column("school_id", sa.String(length=26), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(length=26), nullable=True),
        sa.Column("updated_by_id", sa.String(length=26), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ENDED')", name=op.f("ck_memberships_status")),
        sa.CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name=op.f("ck_memberships_date_order")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_memberships_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_memberships_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memberships_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint("user_id", "organization_id", "school_id", name="uq_memberships_user_id_organization_id_school_id", postgresql_nulls_not_distinct=True),
    )
    op.create_index(op.f("ix_memberships_organization_id"), "memberships", ["organization_id"], unique=False)
    op.create_index(op.f("ix_memberships_school_id"), "memberships", ["school_id"], unique=False)
    op.create_index(op.f("ix_memberships_status"), "memberships", ["status"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)

    op.create_table(
        "membership_roles",
        sa.Column("membership_id", sa.String(length=26), nullable=False),
        sa.Column("role_id", sa.String(length=26), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_scope", sa.String(length=20), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(length=26), nullable=True),
        sa.Column("updated_by_id", sa.String(length=26), nullable=True),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], name=op.f("fk_membership_roles_membership_id_memberships"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name=op.f("fk_membership_roles_role_id_roles"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_membership_roles")),
        sa.UniqueConstraint("membership_id", "role_id", name="uq_membership_roles_membership_id_role_id"),
    )
    op.create_index(op.f("ix_membership_roles_membership_id"), "membership_roles", ["membership_id"], unique=False)
    op.create_index(op.f("ix_membership_roles_role_id"), "membership_roles", ["role_id"], unique=False)

    # Functional uniqueness for login identifiers. Partial indexes so users who
    # sign in by phone only (no email) never collide on NULL.
    op.execute(
        "CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email)) "
        "WHERE email IS NOT NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_phone_active ON users (phone) "
        "WHERE phone IS NOT NULL AND deleted_at IS NULL"
    )

    # --- Row-Level Security ----------------------------------------------
    for table in _RLS_SELF_ORG:
        for statement in self_org_policy_sql(table):
            op.execute(statement)
    for table in _RLS_ORG:
        allow_null = table == "roles"
        for statement in org_scoped_policy_sql(table, allow_null_org=allow_null):
            op.execute(statement)


def downgrade() -> None:
    for table in [*_RLS_SELF_ORG, *_RLS_ORG]:
        for statement in drop_policy_sql(table):
            op.execute(statement)

    op.execute("DROP INDEX IF EXISTS uq_users_phone_active")
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")

    for table in reversed(_CREATED):
        op.drop_table(table)