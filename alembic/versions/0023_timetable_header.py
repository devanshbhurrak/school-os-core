"""0023 — Timetable header entity with DRAFT/PUBLISHED/ARCHIVED lifecycle."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import school_scoped_policy_sql

revision = "0023_timetable_header"
down_revision = "0022_parents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- timetables table --
    op.create_table(
        "timetables",
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("school_id", sa.String(26), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("academic_year_id", sa.String(26), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_id", sa.String(26), nullable=True),
        sa.Column("updated_by_id", sa.String(26), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name=op.f("ck_timetables_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timetables")),
    )
    op.create_index(op.f("ix_timetables_school_id"), "timetables", ["school_id"], unique=False)
    op.create_index(
        "ix_timetables_school_year_status",
        "timetables",
        ["school_id", "academic_year_id", "status"],
        unique=False,
    )

    # -- Add timetable_id to timetable_slots --
    op.add_column(
        "timetable_slots",
        sa.Column("timetable_id", sa.String(26), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_timetable_slots_timetable_id_timetables"),
        "timetable_slots",
        "timetables",
        ["timetable_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # -- RLS --
    for stmt in school_scoped_policy_sql("timetables"):
        op.execute(stmt)


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_timetable_slots_timetable_id_timetables"),
        "timetable_slots",
        type_="foreignkey",
    )
    op.drop_column("timetable_slots", "timetable_id")
    op.drop_index("ix_timetables_school_year_status", table_name="timetables")
    op.drop_index(op.f("ix_timetables_school_id"), table_name="timetables")
    op.drop_table("timetables")
