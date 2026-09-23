"""0015 — Attendance sessions and records tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0015_attendance"
down_revision = "0014_timetables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_sessions",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("cohort_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_id", sa.String(26), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'AMENDED')",
            name=op.f("ck_attendance_sessions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_attendance_sessions_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_attendance_sessions_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name=op.f("fk_attendance_sessions_cohort_id_cohorts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"], ["academic_years.id"],
            name=op.f("fk_attendance_sessions_academic_year_id_academic_years"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"], ["users.id"],
            name=op.f("fk_attendance_sessions_submitted_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attendance_sessions")),
        sa.UniqueConstraint("cohort_id", "session_date", name="uq_attendance_session_cohort_date"),
    )
    op.create_index(op.f("ix_attendance_sessions_school_id"), "attendance_sessions", ["school_id"], unique=False)
    op.create_index(op.f("ix_attendance_sessions_cohort_id"), "attendance_sessions", ["cohort_id"], unique=False)

    op.create_table(
        "attendance_records",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("session_id", sa.String(26), nullable=False),
        sa.Column("enrollment_id", sa.String(26), nullable=False),
        sa.Column("student_id", sa.String(26), nullable=False),
        sa.Column("status", sa.String(20), server_default="PRESENT", nullable=False),
        sa.Column("arrived_at", sa.Time(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED', 'HOLIDAY')",
            name=op.f("ck_attendance_records_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_attendance_records_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_attendance_records_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["attendance_sessions.id"],
            name=op.f("fk_attendance_records_session_id_attendance_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["student_enrollments.id"],
            name=op.f("fk_attendance_records_enrollment_id_student_enrollments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_attendance_records_student_id_students"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attendance_records")),
        sa.UniqueConstraint("session_id", "enrollment_id", name="uq_record_session_enrollment"),
    )
    op.create_index(op.f("ix_attendance_records_school_id"), "attendance_records", ["school_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_session_id"), "attendance_records", ["session_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_enrollment_id"), "attendance_records", ["enrollment_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_student_id"), "attendance_records", ["student_id"], unique=False)

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
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED',"
        "'ATTENDANCE_SESSION_CREATED', 'ATTENDANCE_SESSION_UPDATED', 'ATTENDANCE_SESSION_DELETED',"
        "'ATTENDANCE_SESSION_SUBMITTED', 'ATTENDANCE_SESSION_AMENDED', 'ATTENDANCE_SESSION_BULK_UPDATED',"
        "'ATTENDANCE_RECORD_UPDATED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("attendance_sessions"):
        op.execute(stmt)
    for stmt in school_scoped_policy_sql("attendance_records"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("attendance_records"):
        op.execute(stmt)
    for stmt in drop_policy_sql("attendance_sessions"):
        op.execute(stmt)

    op.drop_index(op.f("ix_attendance_records_student_id"), table_name="attendance_records")
    op.drop_index(op.f("ix_attendance_records_enrollment_id"), table_name="attendance_records")
    op.drop_index(op.f("ix_attendance_records_session_id"), table_name="attendance_records")
    op.drop_index(op.f("ix_attendance_records_school_id"), table_name="attendance_records")
    op.drop_table("attendance_records")

    op.drop_index(op.f("ix_attendance_sessions_cohort_id"), table_name="attendance_sessions")
    op.drop_index(op.f("ix_attendance_sessions_school_id"), table_name="attendance_sessions")
    op.drop_table("attendance_sessions")

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
        "'STUDENT_CREATED', 'STUDENT_UPDATED', 'STUDENT_DELETED',"
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED'"
        "))"
    )
