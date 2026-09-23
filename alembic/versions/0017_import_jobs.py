"""0017 — Import jobs table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0017_import_jobs"
down_revision = "0016_announcements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", JSONB(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "resource_type IN ('students', 'teachers')",
            name=op.f("ck_import_jobs_resource_type"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL')",
            name=op.f("ck_import_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_import_jobs_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_import_jobs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(op.f("ix_import_jobs_school_id"), "import_jobs", ["school_id"], unique=False)

    # Extend audit_logs action check constraint to include import_job actions
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
        "'STUDENT_GUARDIAN_CREATED', 'STUDENT_GUARDIAN_UPDATED', 'STUDENT_GUARDIAN_DELETED',"
        "'TEACHER_CREATED', 'TEACHER_UPDATED', 'TEACHER_DELETED',"
        "'TEACHER_ASSIGNED', 'TEACHER_ASSIGNMENT_UPDATED', 'TEACHER_ASSIGNMENT_ENDED',"
        "'PERIOD_DEFINITION_CREATED', 'PERIOD_DEFINITION_UPDATED', 'PERIOD_DEFINITION_DELETED',"
        "'TIMETABLE_SLOT_CREATED', 'TIMETABLE_SLOT_UPDATED', 'TIMETABLE_SLOT_CANCELLED',"
        "'ANNOUNCEMENT_CREATED', 'ANNOUNCEMENT_UPDATED', 'ANNOUNCEMENT_DELETED',"
        "'ANNOUNCEMENT_PUBLISHED', 'ANNOUNCEMENT_ARCHIVED',"
        "'ATTENDANCE_SESSION_CREATED', 'ATTENDANCE_SESSION_UPDATED', 'ATTENDANCE_SESSION_DELETED',"
        "'ATTENDANCE_SESSION_SUBMITTED', 'ATTENDANCE_SESSION_AMENDED', 'ATTENDANCE_SESSION_BULK_UPDATED',"
        "'ATTENDANCE_RECORD_UPDATED',"
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED',"
        "'IMPORT_JOB_CREATED', 'IMPORT_JOB_COMPLETED', 'IMPORT_JOB_FAILED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("import_jobs"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("import_jobs"):
        op.execute(stmt)

    op.drop_index(op.f("ix_import_jobs_school_id"), table_name="import_jobs")
    op.drop_table("import_jobs")

    # Restore prior audit_logs action check constraint (0016 state)
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
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED',"
        "'STUDENT_GUARDIAN_CREATED', 'STUDENT_GUARDIAN_UPDATED', 'STUDENT_GUARDIAN_DELETED',"
        "'TEACHER_CREATED', 'TEACHER_UPDATED', 'TEACHER_DELETED',"
        "'TEACHER_ASSIGNED', 'TEACHER_ASSIGNMENT_UPDATED', 'TEACHER_ASSIGNMENT_ENDED',"
        "'PERIOD_DEFINITION_CREATED', 'PERIOD_DEFINITION_UPDATED', 'PERIOD_DEFINITION_DELETED',"
        "'TIMETABLE_SLOT_CREATED', 'TIMETABLE_SLOT_UPDATED', 'TIMETABLE_SLOT_CANCELLED',"
        "'ANNOUNCEMENT_CREATED', 'ANNOUNCEMENT_UPDATED', 'ANNOUNCEMENT_DELETED',"
        "'ANNOUNCEMENT_PUBLISHED', 'ANNOUNCEMENT_ARCHIVED',"
        "'ATTENDANCE_SESSION_CREATED', 'ATTENDANCE_SESSION_UPDATED', 'ATTENDANCE_SESSION_DELETED',"
        "'ATTENDANCE_SESSION_SUBMITTED', 'ATTENDANCE_SESSION_AMENDED', 'ATTENDANCE_SESSION_BULK_UPDATED',"
        "'ATTENDANCE_RECORD_UPDATED'"
        "))"
    )
