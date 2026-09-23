"""0009 — Partial unique index: only one is_current academic year per school.

Prevents two concurrent requests from both setting is_current=True for the
same school. The partial index (WHERE is_current = true AND deleted_at IS NULL)
enforces the invariant at the database level as a last line of defence.
"""
from __future__ import annotations

from alembic import op

revision = "0009_academic_year_current_unique"
down_revision = "0008_actor_columns_org_school"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_academic_years_one_current_per_school
            ON academic_years (school_id)
            WHERE is_current = true AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_academic_years_one_current_per_school")
