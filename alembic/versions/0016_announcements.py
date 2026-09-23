"""0016 — Announcements: announcements and announcement_targets tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0016_announcements"
down_revision = "0015_attendance"
branch_labels = None
depends_on = None

_TABLES = ["announcements", "announcement_targets"]


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), server_default="NORMAL", nullable=False),
        sa.Column("publish_mode", sa.String(20), server_default="IMMEDIATE", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("priority IN ('NORMAL', 'HIGH', 'URGENT')", name="ck_announcements_priority"),
        sa.CheckConstraint("publish_mode IN ('IMMEDIATE', 'SCHEDULED')", name="ck_announcements_publish_mode"),
        sa.CheckConstraint("status IN ('DRAFT', 'PUBLISHED', 'EXPIRED', 'ARCHIVED')", name="ck_announcements_status"),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_announcements_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_announcements_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcements")),
    )
    op.create_index(op.f("ix_announcements_school_id"), "announcements", ["school_id"], unique=False)
    op.create_index(op.f("ix_announcements_organization_id"), "announcements", ["organization_id"], unique=False)
    op.create_index(
        "ix_announcements_school_status_published",
        "announcements", ["school_id", "status", "published_at"], unique=False,
    )

    op.create_table(
        "announcement_targets",
        sa.Column("announcement_id", sa.String(26), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(26), nullable=True),
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "target_type IN ('SCHOOL', 'CLASS', 'COHORT', 'ROLE')",
            name="ck_announcement_targets_target_type",
        ),
        sa.ForeignKeyConstraint(
            ["announcement_id"], ["announcements.id"],
            name=op.f("fk_announcement_targets_announcement_id_announcements"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_announcement_targets_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_announcement_targets_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcement_targets")),
    )
    op.create_index(
        op.f("ix_announcement_targets_announcement_id"),
        "announcement_targets", ["announcement_id"], unique=False,
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

    for table in _TABLES:
        for stmt in school_scoped_policy_sql(table):
            op.execute(stmt)


def downgrade() -> None:
    for table in reversed(_TABLES):
        for stmt in drop_policy_sql(table):
            op.execute(stmt)
    op.drop_table("announcement_targets")
    op.drop_table("announcements")

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
        "'ENROLLMENT_CREATED', 'ENROLLMENT_UPDATED', 'ENROLLMENT_DELETED',"
        "'STUDENT_GUARDIAN_CREATED', 'STUDENT_GUARDIAN_UPDATED', 'STUDENT_GUARDIAN_DELETED',"
        "'TEACHER_CREATED', 'TEACHER_UPDATED', 'TEACHER_DELETED',"
        "'TEACHER_ASSIGNED', 'TEACHER_ASSIGNMENT_UPDATED', 'TEACHER_ASSIGNMENT_ENDED',"
        "'PERIOD_DEFINITION_CREATED', 'PERIOD_DEFINITION_UPDATED', 'PERIOD_DEFINITION_DELETED',"
        "'TIMETABLE_SLOT_CREATED', 'TIMETABLE_SLOT_UPDATED', 'TIMETABLE_SLOT_CANCELLED'"
        "))"
    )
