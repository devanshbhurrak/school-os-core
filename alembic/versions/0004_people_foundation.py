"""0004 — People foundation: addresses, persons, contacts.

Also closes the deferred foreign keys created in 0002 (users.person_id,
schools.address_id) now that the referenced tables exist.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.rls import (
    ORG_SCOPED_TABLES,
    drop_policy_sql,
    org_scoped_policy_sql,
)

revision = "0004_people_foundation"
down_revision = "0003_auth_tables"
branch_labels = None
depends_on = None

_CREATED = ["addresses", "persons", "contacts"]
_RLS_ORG = [t for t in ORG_SCOPED_TABLES if t in _CREATED]


def upgrade() -> None:
    # pg_trgm powers fuzzy duplicate-person detection and name search.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "addresses",
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_id", sa.String(length=26), nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=False),
        sa.Column("address_type", sa.String(length=24), server_default="RESIDENTIAL", nullable=False),
        sa.Column("line1", sa.String(length=200), nullable=True),
        sa.Column("line2", sa.String(length=200), nullable=True),
        sa.Column("landmark", sa.String(length=160), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("country_code", sa.String(length=2), server_default="IN", nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("address_type IN ('RESIDENTIAL', 'PERMANENT', 'CORRESPONDENCE', 'CAMPUS', 'OTHER')", name=op.f("ck_addresses_address_type")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_addresses_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_addresses")),
    )
    op.create_index("ix_addresses_entity", "addresses", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_addresses_organization_id"), "addresses", ["organization_id"], unique=False)

    op.create_table(
        "persons",
        sa.Column("organization_id", sa.String(length=26), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("preferred_name", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=24), nullable=True),
        sa.Column("blood_group", sa.String(length=8), nullable=True),
        sa.Column("nationality", sa.String(length=60), nullable=True),
        sa.Column("primary_phone", sa.String(length=24), nullable=True),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("address_id", sa.String(length=26), nullable=True),
        sa.Column("photo_document_id", sa.String(length=26), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="ACTIVE", nullable=False),
        sa.Column("merged_into_person_id", sa.String(length=26), nullable=True),
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(length=26), nullable=True),
        sa.Column("updated_by_id", sa.String(length=26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'DECEASED', 'MERGED')", name=op.f("ck_persons_status")),
        sa.CheckConstraint("merged_into_person_id IS NULL OR merged_into_person_id <> id", name=op.f("ck_persons_merge_not_self")),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"], name=op.f("fk_persons_address_id_addresses"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merged_into_person_id"], ["persons.id"], name=op.f("fk_persons_merged_into_person_id_persons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_persons_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persons")),
    )
    op.create_index(op.f("ix_persons_organization_id"), "persons", ["organization_id"], unique=False)
    op.create_index(op.f("ix_persons_date_of_birth"), "persons", ["date_of_birth"], unique=False)
    op.create_index(op.f("ix_persons_primary_email"), "persons", ["primary_email"], unique=False)
    op.create_index(op.f("ix_persons_primary_phone"), "persons", ["primary_phone"], unique=False)
    op.create_index("ix_persons_organization_id_last_name", "persons", ["organization_id", "last_name"], unique=False)

    op.create_table(
        "contacts",
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_id", sa.String(length=26), nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=False),
        sa.Column("contact_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_emergency", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("contact_type IN ('PHONE', 'EMAIL', 'WHATSAPP')", name=op.f("ck_contacts_contact_type")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_contacts_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
        sa.UniqueConstraint("entity_type", "entity_id", "contact_type", "value", name="uq_contacts_entity_type_entity_id_contact_type_value"),
    )
    op.create_index("ix_contacts_entity", "contacts", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_contacts_organization_id"), "contacts", ["organization_id"], unique=False)

    # Trigram index over the full person name for duplicate detection / search.
    op.execute(
        "CREATE INDEX ix_persons_name_trgm ON persons USING gin ("
        "(coalesce(first_name,'') || ' ' || coalesce(middle_name,'') || ' ' || "
        "coalesce(last_name,'')) gin_trgm_ops)"
    )

    # Deferred foreign keys from 0002, now that the targets exist.
    op.create_foreign_key(
        op.f("fk_users_person_id_persons"),
        "users", "persons", ["person_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_users_person_id"), "users", ["person_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_schools_address_id_addresses"),
        "schools", "addresses", ["address_id"], ["id"], ondelete="SET NULL",
    )

    # --- Row-Level Security ----------------------------------------------
    for table in _RLS_ORG:
        for statement in org_scoped_policy_sql(table):
            op.execute(statement)


def downgrade() -> None:
    for table in _RLS_ORG:
        for statement in drop_policy_sql(table):
            op.execute(statement)

    op.execute("DROP INDEX IF EXISTS ix_persons_name_trgm")
    op.drop_index(op.f("ix_users_person_id"), table_name="users")
    op.drop_constraint(op.f("fk_schools_address_id_addresses"), "schools", type_="foreignkey")
    op.drop_constraint(op.f("fk_users_person_id_persons"), "users", type_="foreignkey")

    for table in reversed(_CREATED):
        op.drop_table(table)