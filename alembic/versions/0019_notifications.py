"""0019 — Notifications table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.rls import drop_policy_sql, org_scoped_policy_sql

revision = "0019_notifications"
down_revision = "0018_user_actor_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.String(26), nullable=False),
        sa.Column("school_id", sa.String(26), nullable=True),
        sa.Column("organization_id", sa.String(26), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("related_entity_type", sa.String(100), nullable=True),
        sa.Column("related_entity_id", sa.String(26), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "type IN ('ANNOUNCEMENT', 'ATTENDANCE', 'ENROLLMENT', 'SYSTEM')",
            name=op.f("ck_notifications_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )

    # Row-Level Security
    for stmt in org_scoped_policy_sql("notifications"):
        op.execute(stmt)


def downgrade() -> None:
    for stmt in drop_policy_sql("notifications"):
        op.execute(stmt)

    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
