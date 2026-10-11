"""0025 — outbox dispatch claim columns (Phase 3, A6 dispatcher)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_outbox_dispatch_claim"
down_revision = "0024_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("locked_by", sa.String(128), nullable=True))
    op.add_column("outbox_events", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_outbox_events_locked_at
        ON outbox_events (locked_at)
        WHERE status = 'PROCESSING'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_outbox_events_locked_at")
    op.drop_column("outbox_events", "locked_at")
    op.drop_column("outbox_events", "locked_by")
