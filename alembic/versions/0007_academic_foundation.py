"""0007 — Academic foundation: academic years, terms, classes, subjects, class_subjects, cohorts."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import SCHOOL_SCOPED_TABLES, drop_policy_sql, school_scoped_policy_sql

revision = "0007_academic_foundation"
down_revision = "0006_permissive_rls"
branch_labels = None
depends_on = None

_CREATED = [
    "academic_years",
    "academic_terms",
    "academic_classes",
    "subjects",
    "class_subjects",
    "cohorts",
]
_RLS_SCHOOL = [t for t in SCHOOL_SCOPED_TABLES if t in _CREATED]


def upgrade() -> None:
    op.create_table(
        "academic_years",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'CLOSED')", name=op.f("ck_academic_years_status")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_academic_years_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_academic_years_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_years")),
        sa.UniqueConstraint("school_id", "code", name="uq_academic_years_school_id_code"),
    )
    op.create_index(op.f("ix_academic_years_school_id"), "academic_years", ["school_id"], unique=False)
    op.create_index(op.f("ix_academic_years_organization_id"), "academic_years", ["organization_id"], unique=False)
    op.create_index("ix_academic_years_school_id_is_current", "academic_years", ["school_id", "is_current"], unique=False)

    op.create_table(
        "academic_terms",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'CLOSED')", name=op.f("ck_academic_terms_status")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_academic_terms_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_academic_terms_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], name=op.f("fk_academic_terms_academic_year_id_academic_years"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_terms")),
        sa.UniqueConstraint("school_id", "academic_year_id", "code", name="uq_academic_terms_school_year_code"),
    )
    op.create_index(op.f("ix_academic_terms_school_id"), "academic_terms", ["school_id"], unique=False)
    op.create_index(op.f("ix_academic_terms_organization_id"), "academic_terms", ["organization_id"], unique=False)
    op.create_index(op.f("ix_academic_terms_academic_year_id"), "academic_terms", ["academic_year_id"], unique=False)

    op.create_table(
        "academic_classes",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name=op.f("ck_academic_classes_status")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_academic_classes_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_academic_classes_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_classes")),
        sa.UniqueConstraint("school_id", "code", name="uq_academic_classes_school_id_code"),
    )
    op.create_index(op.f("ix_academic_classes_school_id"), "academic_classes", ["school_id"], unique=False)
    op.create_index(op.f("ix_academic_classes_organization_id"), "academic_classes", ["organization_id"], unique=False)

    op.create_table(
        "subjects",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("subject_type", sa.String(30), server_default="CORE", nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "subject_type IN ('CORE', 'OPTIONAL', 'ELECTIVE', 'PRACTICAL', 'CO_CURRICULAR', 'ACTIVITY')",
            name=op.f("ck_subjects_subject_type"),
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name=op.f("ck_subjects_status")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_subjects_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_subjects_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint("school_id", "code", name="uq_subjects_school_id_code"),
    )
    op.create_index(op.f("ix_subjects_school_id"), "subjects", ["school_id"], unique=False)
    op.create_index(op.f("ix_subjects_organization_id"), "subjects", ["organization_id"], unique=False)

    op.create_table(
        "class_subjects",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_class_id", sa.String(26), nullable=False),
        sa.Column("subject_id", sa.String(26), nullable=False),
        sa.Column("effective_from_year_id", sa.String(26), nullable=False),
        sa.Column("effective_to_year_id", sa.String(26), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_class_subjects_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_class_subjects_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_class_id"], ["academic_classes.id"], name=op.f("fk_class_subjects_academic_class_id_academic_classes"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name=op.f("fk_class_subjects_subject_id_subjects"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["effective_from_year_id"], ["academic_years.id"], name=op.f("fk_class_subjects_effective_from_year_id_academic_years"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["effective_to_year_id"], ["academic_years.id"], name=op.f("fk_class_subjects_effective_to_year_id_academic_years"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_class_subjects")),
        sa.UniqueConstraint("school_id", "academic_class_id", "subject_id", name="uq_class_subjects_school_class_subject"),
    )
    op.create_index(op.f("ix_class_subjects_school_id"), "class_subjects", ["school_id"], unique=False)
    op.create_index(op.f("ix_class_subjects_organization_id"), "class_subjects", ["organization_id"], unique=False)
    op.create_index(op.f("ix_class_subjects_academic_class_id"), "class_subjects", ["academic_class_id"], unique=False)
    op.create_index(op.f("ix_class_subjects_subject_id"), "class_subjects", ["subject_id"], unique=False)
    op.create_index("ix_class_subjects_effective_from_year_id", "class_subjects", ["effective_from_year_id"], unique=False)

    op.create_table(
        "cohorts",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("academic_class_id", sa.String(26), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name=op.f("ck_cohorts_status")),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], name=op.f("fk_cohorts_school_id_schools"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_cohorts_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], name=op.f("fk_cohorts_academic_year_id_academic_years"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_class_id"], ["academic_classes.id"], name=op.f("fk_cohorts_academic_class_id_academic_classes"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cohorts")),
        sa.UniqueConstraint("school_id", "academic_year_id", "academic_class_id", "code", name="uq_cohorts_school_year_class_code"),
    )
    op.create_index(op.f("ix_cohorts_school_id"), "cohorts", ["school_id"], unique=False)
    op.create_index(op.f("ix_cohorts_organization_id"), "cohorts", ["organization_id"], unique=False)
    op.create_index(op.f("ix_cohorts_academic_year_id"), "cohorts", ["academic_year_id"], unique=False)
    op.create_index(op.f("ix_cohorts_academic_class_id"), "cohorts", ["academic_class_id"], unique=False)

    # --- Extend audit_logs action check constraint ---
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_logs_action")
    op.execute(
        "ALTER TABLE audit_logs ADD CONSTRAINT ck_audit_logs_action CHECK (action IN ("
        "'ORGANIZATION_CREATED', 'ORGANIZATION_UPDATED', 'ORGANIZATION_DELETED',"
        "'SCHOOL_CREATED', 'SCHOOL_UPDATED', 'SCHOOL_DELETED',"
        "'USER_CREATED', 'USER_UPDATED', 'USER_DELETED',"
        "'MEMBERSHIP_CREATED', 'MEMBERSHIP_UPDATED', 'MEMBERSHIP_ENDED',"
        "'ROLE_CREATED', 'ROLE_UPDATED', 'ROLE_DELETED', 'ROLE_GRANTED', 'ROLE_REVOKED',"
        "'PERSON_CREATED', 'PERSON_UPDATED', 'PERSON_DELETED', 'PERSON_MERGED',"
        "'ADDRESS_CREATED', 'ADDRESS_UPDATED', 'ADDRESS_DELETED',"
        "'CONTACT_CREATED', 'CONTACT_UPDATED', 'CONTACT_DELETED',"
        "'LOGIN_SUCCESS', 'LOGOUT', 'PASSWORD_CHANGED', 'PASSWORD_RESET_REQUESTED', 'PASSWORD_RESET_CONFIRMED',"
        "'ACADEMIC_YEAR_CREATED', 'ACADEMIC_YEAR_UPDATED', 'ACADEMIC_YEAR_DELETED',"
        "'ACADEMIC_TERM_CREATED', 'ACADEMIC_TERM_UPDATED', 'ACADEMIC_TERM_DELETED',"
        "'ACADEMIC_CLASS_CREATED', 'ACADEMIC_CLASS_UPDATED', 'ACADEMIC_CLASS_DELETED',"
        "'SUBJECT_CREATED', 'SUBJECT_UPDATED', 'SUBJECT_DELETED',"
        "'CLASS_SUBJECT_CREATED', 'CLASS_SUBJECT_DELETED',"
        "'COHORT_CREATED', 'COHORT_UPDATED', 'COHORT_DELETED'"
        "))"
    )

    # --- Row-Level Security ---
    for table in _RLS_SCHOOL:
        for stmt in school_scoped_policy_sql(table):
            op.execute(stmt)


def downgrade() -> None:
    for table in _RLS_SCHOOL:
        for stmt in drop_policy_sql(table):
            op.execute(stmt)

    for table in reversed(_CREATED):
        op.drop_table(table)

    # Restore the original audit_logs action check constraint
    op.execute("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_logs_action")
    op.execute(
        "ALTER TABLE audit_logs ADD CONSTRAINT ck_audit_logs_action CHECK (action IN ("
        "'ORGANIZATION_CREATED', 'ORGANIZATION_UPDATED', 'ORGANIZATION_DELETED',"
        "'SCHOOL_CREATED', 'SCHOOL_UPDATED', 'SCHOOL_DELETED',"
        "'USER_CREATED', 'USER_UPDATED', 'USER_DELETED',"
        "'MEMBERSHIP_CREATED', 'MEMBERSHIP_UPDATED', 'MEMBERSHIP_ENDED',"
        "'ROLE_CREATED', 'ROLE_UPDATED', 'ROLE_DELETED', 'ROLE_GRANTED', 'ROLE_REVOKED',"
        "'PERSON_CREATED', 'PERSON_UPDATED', 'PERSON_DELETED', 'PERSON_MERGED',"
        "'ADDRESS_CREATED', 'ADDRESS_UPDATED', 'ADDRESS_DELETED',"
        "'CONTACT_CREATED', 'CONTACT_UPDATED', 'CONTACT_DELETED',"
        "'LOGIN_SUCCESS', 'LOGOUT', 'PASSWORD_CHANGED', 'PASSWORD_RESET_REQUESTED', 'PASSWORD_RESET_CONFIRMED'"
        "))"
    )
