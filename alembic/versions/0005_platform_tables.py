"""0005 — Platform tables: audit log, outbox, background jobs, feature flags.

These tables carry nullable tenant columns and are **exempt from RLS** — a failed
login has no school yet, and an audit row may precede any tenancy. The exemption
list is asserted in tests/integration/test_rls_coverage.py.

The audit log is append-only: a trigger rejects UPDATE and DELETE so a row, once
committed, is immutable (TRUNCATE, run by operators, still works).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_platform_tables"
down_revision = "0004_people_foundation"
branch_labels = None
depends_on = None

_TABLES = ["audit_logs", "outbox_events", "background_jobs", "feature_flags"]


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("organization_id", sa.String(length=26), nullable=True),
        sa.Column("school_id", sa.String(length=26), nullable=True),
        sa.Column("actor_user_id", sa.String(length=26), nullable=True),
        sa.Column("actor_label", sa.String(length=200), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=26), nullable=True),
        sa.Column("summary", sa.String(length=400), nullable=True),
        sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("action IN ('ORGANIZATION_CREATED', 'ORGANIZATION_UPDATED', 'ORGANIZATION_DELETED', 'SCHOOL_CREATED', 'SCHOOL_UPDATED', 'SCHOOL_DELETED', 'USER_CREATED', 'USER_UPDATED', 'USER_DELETED', 'MEMBERSHIP_CREATED', 'MEMBERSHIP_UPDATED', 'MEMBERSHIP_ENDED', 'ROLE_CREATED', 'ROLE_UPDATED', 'ROLE_DELETED', 'ROLE_GRANTED', 'ROLE_REVOKED', 'PERSON_CREATED', 'PERSON_UPDATED', 'PERSON_DELETED', 'PERSON_MERGED', 'ADDRESS_CREATED', 'ADDRESS_UPDATED', 'ADDRESS_DELETED', 'CONTACT_CREATED', 'CONTACT_UPDATED', 'CONTACT_DELETED', 'LOGIN_SUCCESS', 'LOGOUT', 'PASSWORD_CHANGED', 'PASSWORD_RESET_REQUESTED', 'PASSWORD_RESET_CONFIRMED')", name=op.f("ck_audit_logs_action")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_request_id"), "audit_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_school_id"), "audit_logs", ["school_id"], unique=False)
    op.create_index("ix_audit_logs_school_id_created_at", "audit_logs", ["school_id", "created_at"], unique=False)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_no_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_no_mutation();
        """
    )

    op.create_table(
        "outbox_events",
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("event_version", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=True),
        sa.Column("school_id", sa.String(length=26), nullable=True),
        sa.Column("actor_user_id", sa.String(length=26), nullable=True),
        sa.Column("entity_type", sa.String(length=60), nullable=True),
        sa.Column("entity_id", sa.String(length=26), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'PROCESSING', 'SENT', 'FAILED')", name=op.f("ck_outbox_events_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_events_dispatch",
        "outbox_events",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('PENDING', 'FAILED')"),
    )
    op.create_index("ix_outbox_events_event_name_created_at", "outbox_events", ["event_name", "created_at"], unique=False)

    op.create_table(
        "background_jobs",
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="QUEUED", nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=True),
        sa.Column("school_id", sa.String(length=26), nullable=True),
        sa.Column("created_by_id", sa.String(length=26), nullable=True),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("progress_done", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')", name=op.f("ck_background_jobs_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_background_jobs")),
    )
    op.create_index(op.f("ix_background_jobs_job_type"), "background_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_background_jobs_organization_id"), "background_jobs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_background_jobs_school_id"), "background_jobs", ["school_id"], unique=False)

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("organization_id", sa.String(length=26), nullable=True),
        sa.Column("school_id", sa.String(length=26), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feature_flags")),
        sa.UniqueConstraint("key", "organization_id", "school_id", name="uq_feature_flags_key_organization_id_school_id", postgresql_nulls_not_distinct=True),
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_no_mutation()")

    for table in reversed(_TABLES):
        op.drop_table(table)