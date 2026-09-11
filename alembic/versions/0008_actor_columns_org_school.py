"""0008 — Add actor columns (created_by_id, updated_by_id) to organizations and schools.

Organizations and Schools were missing ActorMixin. The service layer already
attempted to set these fields; the migration makes them persist properly.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_actor_columns_org_school"
down_revision = "0007_academic_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("created_by_id", sa.String(26), nullable=True))
    op.add_column("organizations", sa.Column("updated_by_id", sa.String(26), nullable=True))

    op.add_column("schools", sa.Column("created_by_id", sa.String(26), nullable=True))
    op.add_column("schools", sa.Column("updated_by_id", sa.String(26), nullable=True))


def downgrade() -> None:
    op.drop_column("schools", "updated_by_id")
    op.drop_column("schools", "created_by_id")

    op.drop_column("organizations", "updated_by_id")
    op.drop_column("organizations", "created_by_id")
