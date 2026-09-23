"""0014 — period_definitions and timetable_slots tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, school_scoped_policy_sql

revision = "0014_timetables"
down_revision = "0013_teachers"
branch_labels = None
depends_on = None

_TABLES = ["period_definitions", "timetable_slots"]


def upgrade() -> None:
    op.create_table(
        "period_definitions",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("period_type", sa.String(20), server_default="LESSON", nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "period_type IN ('LESSON', 'BREAK', 'LUNCH', 'ASSEMBLY', 'FREE', 'EXAM')",
            name=op.f("ck_period_definitions_period_type"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_period_definitions_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_period_definitions_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"], ["academic_years.id"],
            name=op.f("fk_period_definitions_academic_year_id_academic_years"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_period_definitions")),
        sa.UniqueConstraint(
            "school_id", "academic_year_id", "name",
            name="uq_period_def_school_year_name",
        ),
    )
    op.create_index(op.f("ix_period_definitions_school_id"), "period_definitions", ["school_id"], unique=False)

    op.create_table(
        "timetable_slots",
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("cohort_id", sa.String(26), nullable=False),
        sa.Column("period_definition_id", sa.String(26), nullable=False),
        sa.Column("teacher_id", sa.String(26), nullable=False),
        sa.Column("subject_id", sa.String(26), nullable=False),
        sa.Column("day_of_week", sa.String(10), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.CheckConstraint(
            "day_of_week IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')",
            name=op.f("ck_timetable_slots_day_of_week"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'CANCELLED', 'SUBSTITUTED')",
            name=op.f("ck_timetable_slots_status"),
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"],
            name=op.f("fk_timetable_slots_school_id_schools"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_timetable_slots_organization_id_organizations"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_year_id"], ["academic_years.id"],
            name=op.f("fk_timetable_slots_academic_year_id_academic_years"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"], ["cohorts.id"],
            name=op.f("fk_timetable_slots_cohort_id_cohorts"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["period_definition_id"], ["period_definitions.id"],
            name=op.f("fk_timetable_slots_period_definition_id_period_definitions"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["teachers.id"],
            name=op.f("fk_timetable_slots_teacher_id_teachers"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"],
            name=op.f("fk_timetable_slots_subject_id_subjects"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timetable_slots")),
        sa.UniqueConstraint(
            "cohort_id", "period_definition_id", "day_of_week", "effective_from",
            name="uq_slot_cohort_period_day_date",
        ),
    )
    op.create_index(op.f("ix_timetable_slots_school_id"), "timetable_slots", ["school_id"], unique=False)
    op.create_index(op.f("ix_timetable_slots_cohort_id"), "timetable_slots", ["cohort_id"], unique=False)
    op.create_index(op.f("ix_timetable_slots_period_definition_id"), "timetable_slots", ["period_definition_id"], unique=False)
    op.create_index(
        "ix_timetable_slots_teacher_id_day_of_week",
        "timetable_slots",
        ["teacher_id", "day_of_week"],
        unique=False,
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
        "'TIMETABLE_SLOT_CREATED', 'TIMETABLE_SLOT_UPDATED', 'TIMETABLE_SLOT_CANCELLED'"
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

    op.drop_index("ix_timetable_slots_teacher_id_day_of_week", table_name="timetable_slots")
    op.drop_index(op.f("ix_timetable_slots_period_definition_id"), table_name="timetable_slots")
    op.drop_index(op.f("ix_timetable_slots_cohort_id"), table_name="timetable_slots")
    op.drop_index(op.f("ix_timetable_slots_school_id"), table_name="timetable_slots")
    op.drop_table("timetable_slots")

    op.drop_index(op.f("ix_period_definitions_school_id"), table_name="period_definitions")
    op.drop_table("period_definitions")

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
        "'TEACHER_ASSIGNED', 'TEACHER_ASSIGNMENT_UPDATED', 'TEACHER_ASSIGNMENT_ENDED'"
        "))"
    )
