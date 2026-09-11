"""Platform-wide models: audit, outbox, feature flags, background jobs.

These tables carry a *nullable* tenant column and are **exempt from RLS** — a
failed login has no school yet, and an audit row may precede any tenancy. Access
is enforced at the API/repository layer, and the exemption list is asserted in
`tests/integration/test_rls_coverage.py`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import PKMixin, TimestampMixin
from app.db.types import ULIDType, enum_check
from app.modules.platform_.enums import AuditAction, JobStatus, OutboxStatus


class AuditLog(PKMixin, TimestampMixin, Base):
    """Append-only record of important actions.

    Written in the same transaction as the domain change — audit is never a
    fire-and-forget. The database enforces immutability via a trigger (migration
    0005). Never log passwords, tokens, or raw secrets.
    """

    __tablename__ = "audit_logs"

    organization_id: Mapped[str | None] = mapped_column(ULIDType, index=True)
    school_id: Mapped[str | None] = mapped_column(ULIDType, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ULIDType, index=True)
    actor_label: Mapped[str | None] = mapped_column(String(200))

    action: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(ULIDType)
    summary: Mapped[str | None] = mapped_column(String(400))
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (
        enum_check("action", AuditAction, "action"),
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_school_id_created_at", "school_id", "created_at"),
    )


class OutboxEvent(PKMixin, Base):
    """Reliable outbox for cross-module / external events.

    Phase 1 ships the table only — no dispatcher. The row is written atomically
    with the domain change; a later worker reads PENDING rows and delivers
    at-least-once. Handlers must be idempotent. Event names are a public
    contract and versioned (`attendance.session_submitted.v1`); renaming one is
    breaking.
    """

    __tablename__ = "outbox_events"

    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    event_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    organization_id: Mapped[str | None] = mapped_column(ULIDType)
    school_id: Mapped[str | None] = mapped_column(ULIDType)
    actor_user_id: Mapped[str | None] = mapped_column(ULIDType)
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(ULIDType)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboxStatus.PENDING.value,
        server_default=OutboxStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        enum_check("status", OutboxStatus, "status"),
        Index(
            "ix_outbox_events_dispatch",
            "next_attempt_at",
            postgresql_where=text("status IN ('PENDING', 'FAILED')"),
        ),
        Index("ix_outbox_events_event_name_created_at", "event_name", "created_at"),
    )


class FeatureFlag(PKMixin, TimestampMixin, Base):
    """Table only in Phase 1: rows, no middleware enforcement, no SDK.

    Future modules enable features per tenant/school (gradual rollout, pilot
    schools, emergency disablement).
    """

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(80), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ULIDType)
    school_id: Mapped[str | None] = mapped_column(ULIDType)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    description: Mapped[str | None] = mapped_column(String(300))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        UniqueConstraint(
            "key", "organization_id", "school_id",
            name="uq_feature_flags_key_organization_id_school_id",
            postgresql_nulls_not_distinct=True,
        ),
    )


class BackgroundJob(PKMixin, TimestampMixin, Base):
    """Table only in Phase 1: jobs are tracked manually or via simple queries.

    Worker infrastructure lands with the first async notification (Milestone 5).
    """

    __tablename__ = "background_jobs"

    job_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.QUEUED.value,
        server_default=JobStatus.QUEUED.value,
    )
    organization_id: Mapped[str | None] = mapped_column(ULIDType, index=True)
    school_id: Mapped[str | None] = mapped_column(ULIDType, index=True)
    created_by_id: Mapped[str | None] = mapped_column(ULIDType)
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    progress_total: Mapped[int | None] = mapped_column(Integer)
    progress_done: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    last_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        enum_check("status", JobStatus, "status"),
    )
