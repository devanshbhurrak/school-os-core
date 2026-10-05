"""0024 — pg_trgm extension and trigram search indexes for persons and students."""
from __future__ import annotations

from alembic import op

revision = "0024_search_indexes"
down_revision = "0023_timetable_header"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS persons_name_trgm
        ON persons USING gin (
            (coalesce(first_name, '') || ' ' || coalesce(last_name, '')) gin_trgm_ops
        )
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS students_admission_trgm
        ON students USING gin (admission_number gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS students_admission_trgm")
    op.execute("DROP INDEX IF EXISTS persons_name_trgm")
