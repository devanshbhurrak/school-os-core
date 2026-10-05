"""0022 — Parents and student_parents tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0022_parents"
down_revision = "0021_export_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("person_id", sa.String(26), nullable=False),
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("occupation", sa.String(200), nullable=True),
        sa.Column("workplace", sa.String(200), nullable=True),
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
            "status IN ('ACTIVE', 'INACTIVE')",
            name=op.f("ck_parents_status"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"],
            name=op.f("fk_parents_person_id_persons"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_parents_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_parents_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parents")),
        sa.UniqueConstraint("school_id", "person_id", name="uq_parents_school_person"),
    )
    op.create_index(op.f("ix_parents_person_id"), "parents", ["person_id"], unique=False)
    op.create_index(op.f("ix_parents_school_id"), "parents", ["school_id"], unique=False)
    op.create_index(op.f("ix_parents_organization_id"), "parents", ["organization_id"], unique=False)

    op.create_table(
        "student_parents",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("student_id", sa.String(26), nullable=False),
        sa.Column("parent_id", sa.String(26), nullable=False),
        sa.Column("relationship", sa.String(30), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_emergency_contact", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_pickup", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "relationship IN ('FATHER', 'MOTHER', 'GUARDIAN', 'GRANDPARENT', 'SIBLING', 'OTHER')",
            name=op.f("ck_student_parents_relationship"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_student_parents_school_id_schools"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_student_parents_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"],
            name=op.f("fk_student_parents_student_id_students"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["parents.id"],
            name=op.f("fk_student_parents_parent_id_parents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_parents")),
        sa.UniqueConstraint("student_id", "parent_id", name="uq_student_parent"),
    )
    op.create_index(op.f("ix_student_parents_school_id"), "student_parents", ["school_id"], unique=False)
    op.create_index(op.f("ix_student_parents_student_id"), "student_parents", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_parents_parent_id"), "student_parents", ["parent_id"], unique=False)

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
        "'REPORT_EXPORTED',"
        "'PARENT_CREATED', 'PARENT_UPDATED', 'PARENT_DELETED',"
        "'STUDENT_PARENT_LINKED', 'STUDENT_PARENT_UNLINKED'"
        "))"
    )

    # Row-Level Security
    for stmt in school_scoped_policy_sql("parents"):
        op.execute(stmt)
    for stmt in school_scoped_policy_sql("student_parents"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("student_parents"):
        op.execute(stmt)
    for stmt in drop_policy_sql("parents"):
        op.execute(stmt)

    op.drop_index(op.f("ix_student_parents_parent_id"), table_name="student_parents")
    op.drop_index(op.f("ix_student_parents_student_id"), table_name="student_parents")
    op.drop_index(op.f("ix_student_parents_school_id"), table_name="student_parents")
    op.drop_table("student_parents")

    op.drop_index(op.f("ix_parents_organization_id"), table_name="parents")
    op.drop_index(op.f("ix_parents_school_id"), table_name="parents")
    op.drop_index(op.f("ix_parents_person_id"), table_name="parents")
    op.drop_table("parents")

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
        "'REPORT_EXPORTED'"
        "))"
    )
