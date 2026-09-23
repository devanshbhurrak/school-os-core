"""0011 — Student enrollments table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0011_enrollments"
down_revision = "0010_students"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_enrollments",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("student_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("academic_class_id", sa.String(26), nullable=False),
        sa.Column("cohort_id", sa.String(26), nullable=False),
        sa.Column("roll_number", sa.String(20), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("enrollment_type", sa.String(24), server_default="REGULAR", nullable=False),
        sa.Column("status", sa.String(24), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'TRANSFERRED', 'WITHDRAWN', 'COMPLETED')",
            name=op.f("ck_student_enrollments_status"),
        ),
        sa.CheckConstraint(
            "enrollment_type IN ('REGULAR', 'TRANSFER_IN', 'REPEAT', 'PROMOTION', 'TEMPORARY')",
            name=op.f("ck_student_enrollments_enrollment_type"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_student_enrollments_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_student_enrollments_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_student_enrollments_student_id_students"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"], ["academic_years.id"],
            name=op.f("fk_student_enrollments_academic_year_id_academic_years"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_class_id"], ["academic_classes.id"],
            name=op.f("fk_student_enrollments_academic_class_id_academic_classes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name=op.f("fk_student_enrollments_cohort_id_cohorts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_enrollments")),
    )
    op.create_index(op.f("ix_student_enrollments_school_id"), "student_enrollments", ["school_id"], unique=False)
    op.create_index(op.f("ix_student_enrollments_student_id"), "student_enrollments", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_enrollments_academic_year_id"), "student_enrollments", ["academic_year_id"], unique=False)
    op.create_index(op.f("ix_student_enrollments_cohort_id"), "student_enrollments", ["cohort_id"], unique=False)

    # Partial unique indexes
    op.execute(
        "CREATE UNIQUE INDEX uq_enrollment_student_year_active "
        "ON student_enrollments (student_id, academic_year_id) "
        "WHERE status = 'ACTIVE'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_enrollment_cohort_roll "
        "ON student_enrollments (cohort_id, roll_number) "
        "WHERE roll_number IS NOT NULL AND status = 'ACTIVE'"
    )

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
        "'STUDENT_CREATED', 'STUDENT_UPDATED', 'STUDENT_DELETED',"
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("student_enrollments"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("student_enrollments"):
        op.execute(stmt)

    op.drop_index("uq_enrollment_cohort_roll", table_name="student_enrollments")
    op.drop_index("uq_enrollment_student_year_active", table_name="student_enrollments")
    op.drop_index(op.f("ix_student_enrollments_cohort_id"), table_name="student_enrollments")
    op.drop_index(op.f("ix_student_enrollments_academic_year_id"), table_name="student_enrollments")
    op.drop_index(op.f("ix_student_enrollments_student_id"), table_name="student_enrollments")
    op.drop_index(op.f("ix_student_enrollments_school_id"), table_name="student_enrollments")
    op.drop_table("student_enrollments")

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
        "'COHORT_CREATED', 'COHORT_UPDATED', 'COHORT_DELETED',"
        "'STUDENT_CREATED', 'STUDENT_UPDATED', 'STUDENT_DELETED'"
        "))"
    )
