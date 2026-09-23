"""0010 — Students table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0010_students"
down_revision = "0009_academic_year_current_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("person_id", sa.String(26), nullable=False),
        sa.Column("admission_number", sa.String(50), nullable=False),
        sa.Column("admission_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(24), server_default="ACTIVE", nullable=False),
        sa.Column("withdrawal_date", sa.Date(), nullable=True),
        sa.Column("withdrawal_reason", sa.String(500), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'WITHDRAWN', 'GRADUATED', 'TRANSFERRED', 'INACTIVE', 'DECEASED')",
            name=op.f("ck_students_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_students_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_students_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"],
            name=op.f("fk_students_person_id_persons"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("school_id", "admission_number", name="uq_students_school_admission_number"),
        sa.UniqueConstraint("school_id", "person_id", name="uq_students_school_person"),
    )
    op.create_index(op.f("ix_students_school_id"), "students", ["school_id"], unique=False)
    op.create_index(op.f("ix_students_organization_id"), "students", ["organization_id"], unique=False)
    op.create_index(op.f("ix_students_person_id"), "students", ["person_id"], unique=False)

    # Extend audit_logs action check constraint
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
        "'COHORT_CREATED', 'COHORT_UPDATED', 'COHORT_DELETED',"
        "'STUDENT_CREATED', 'STUDENT_UPDATED', 'STUDENT_DELETED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("students"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("students"):
        op.execute(stmt)

    op.drop_index(op.f("ix_students_person_id"), table_name="students")
    op.drop_index(op.f("ix_students_organization_id"), table_name="students")
    op.drop_index(op.f("ix_students_school_id"), table_name="students")
    op.drop_table("students")

    # Restore prior audit_logs action check constraint
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
