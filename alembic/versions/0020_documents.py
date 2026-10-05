"""0020 — Documents table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0020_documents"
down_revision = "0019_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(26), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_UPLOAD"),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "entity_type IN ('STUDENT', 'TEACHER', 'PARENT', 'SCHOOL')",
            name=op.f("ck_documents_entity_type"),
        ),
        sa.CheckConstraint(
            "document_type IN ('PHOTO', 'ID_PROOF', 'BIRTH_CERTIFICATE', 'CERTIFICATE', 'TRANSCRIPT', 'REPORT_CARD', 'OTHER')",
            name=op.f("ck_documents_document_type"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING_UPLOAD', 'CONFIRMED', 'DELETED')",
            name=op.f("ck_documents_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_school_id"), "documents", ["school_id"], unique=False)
    op.create_index(op.f("ix_documents_entity"), "documents", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_documents_school_status"), "documents", ["school_id", "status"], unique=False)

    # Extend audit_logs action check constraint to include document actions
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
        "'IMPORT_JOB_CREATED', 'IMPORT_JOB_COMPLETED', 'IMPORT_JOB_FAILED',"
        "'NOTIFICATION_CREATED', 'NOTIFICATION_UPDATED', 'NOTIFICATION_DELETED',"
        "'DOCUMENT_UPLOAD_REQUESTED', 'DOCUMENT_CONFIRMED', 'DOCUMENT_DOWNLOADED', 'DOCUMENT_DELETED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("documents"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("documents"):
        op.execute(stmt)

    op.drop_index(op.f("ix_documents_school_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_entity"), table_name="documents")
    op.drop_index(op.f("ix_documents_school_id"), table_name="documents")
    op.drop_table("documents")

    # Restore prior audit_logs action check constraint (0019 state)
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
        "'IMPORT_JOB_CREATED', 'IMPORT_JOB_COMPLETED', 'IMPORT_JOB_FAILED',"
        "'NOTIFICATION_CREATED', 'NOTIFICATION_UPDATED', 'NOTIFICATION_DELETED'"
        "))"
    )
