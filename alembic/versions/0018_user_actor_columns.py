"""0018 — Add actor columns to users table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_user_actor_columns"
down_revision = "0017_import_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("created_by_id", sa.String(26), nullable=True))
    op.add_column("users", sa.Column("updated_by_id", sa.String(26), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "updated_by_id")
    op.drop_column("users", "created_by_id")
