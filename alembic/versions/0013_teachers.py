"""0013 — Teachers and teacher_assignments tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0013_teachers"
down_revision = "0012_student_guardians"
branch_labels = None
depends_on = None

_TABLES = ["teachers", "teacher_assignments"]


def upgrade() -> None:
    op.create_table(
        "teachers",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("person_id", sa.String(26), nullable=False),
        sa.Column("employee_number", sa.String(50), nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("leaving_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(24), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'ON_LEAVE', 'RESIGNED', 'TERMINATED', 'INACTIVE')",
            name=op.f("ck_teachers_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_teachers_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_teachers_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"],
            name=op.f("fk_teachers_person_id_persons"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teachers")),
        sa.UniqueConstraint("school_id", "person_id", name="uq_teachers_school_id_person_id"),
    )
    op.create_index(op.f("ix_teachers_school_id"), "teachers", ["school_id"], unique=False)
    op.create_index(op.f("ix_teachers_organization_id"), "teachers", ["organization_id"], unique=False)
    op.create_index(op.f("ix_teachers_person_id"), "teachers", ["person_id"], unique=False)
    # Partial unique index: employee_number is unique per school when set and not deleted
    op.execute(
        """
        CREATE UNIQUE INDEX uq_teachers_school_id_employee_number
            ON teachers (school_id, employee_number)
            WHERE employee_number IS NOT NULL AND deleted_at IS NULL
        """
    )

    op.create_table(
        "teacher_assignments",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("teacher_id", sa.String(26), nullable=False),
        sa.Column("cohort_id", sa.String(26), nullable=False),
        sa.Column("subject_id", sa.String(26), nullable=True),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("role", sa.String(30), server_default="SUBJECT_TEACHER", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(24), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "role IN ('SUBJECT_TEACHER', 'CLASS_TEACHER', 'SUBSTITUTE', 'COORDINATOR')",
            name=op.f("ck_teacher_assignments_role"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'ENDED')",
            name=op.f("ck_teacher_assignments_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_teacher_assignments_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_teacher_assignments_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["teachers.id"],
            name=op.f("fk_teacher_assignments_teacher_id_teachers"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name=op.f("fk_teacher_assignments_cohort_id_cohorts"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"],
            name=op.f("fk_teacher_assignments_subject_id_subjects"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"], ["academic_years.id"],
            name=op.f("fk_teacher_assignments_academic_year_id_academic_years"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teacher_assignments")),
    )
    op.create_index(op.f("ix_teacher_assignments_school_id"), "teacher_assignments", ["school_id"], unique=False)
    op.create_index(op.f("ix_teacher_assignments_organization_id"), "teacher_assignments", ["organization_id"], unique=False)
    op.create_index(op.f("ix_teacher_assignments_teacher_id"), "teacher_assignments", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_teacher_assignments_cohort_id"), "teacher_assignments", ["cohort_id"], unique=False)
    op.create_index(op.f("ix_teacher_assignments_academic_year_id"), "teacher_assignments", ["academic_year_id"], unique=False)
    op.create_index("ix_teacher_assignments_subject_id", "teacher_assignments", ["subject_id"], unique=False)

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
        "'TEACHER_ASSIGNED', 'TEACHER_ASSIGNMENT_UPDATED', 'TEACHER_ASSIGNMENT_ENDED'"
        "))"
    )

    # Row-Level Security
    for table in _TABLES:
        for stmt in school_scoped_policy_sql(table):
            op.execute(stmt)


def downgrade() -> None:
    for table in reversed(_TABLES):
        for stmt in drop_policy_sql(table):
            op.execute(stmt)

    op.drop_index("ix_teacher_assignments_subject_id", table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_academic_year_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_cohort_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_teacher_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_organization_id"), table_name="teacher_assignments")
    op.drop_index(op.f("ix_teacher_assignments_school_id"), table_name="teacher_assignments")
    op.drop_table("teacher_assignments")

    op.execute("DROP INDEX IF EXISTS uq_teachers_school_id_employee_number")
    op.drop_index(op.f("ix_teachers_person_id"), table_name="teachers")
    op.drop_index(op.f("ix_teachers_organization_id"), table_name="teachers")
    op.drop_index(op.f("ix_teachers_school_id"), table_name="teachers")
    op.drop_table("teachers")

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
        "'STUDENT_GUARDIAN_CREATED', 'STUDENT_GUARDIAN_UPDATED', 'STUDENT_GUARDIAN_DELETED'"
        "))"
    )
