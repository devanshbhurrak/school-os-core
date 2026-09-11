"""Shared model mixins.

These enforce the "historical truth" rule (PRD §6.2) structurally rather than
by convention:

* `TimestampMixin` — DB-generated UTC created/updated.
* `ActorMixin`    — who created and last touched the row (audit metadata).
* `VersionMixin`  — optimistic locking; a stale write raises, never overwrites.
* `SoftDeleteMixin` — `archived_at` (withdrawn but still referenced) vs
  `deleted_at` (retention-policy removal). Default queries exclude both.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import ULIDType, gen_ulid


class PKMixin:
    """26-char ULID primary key, generated client-side."""

    id: Mapped[str] = mapped_column(ULIDType, primary_key=True, default=gen_ulid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class ActorMixin:
    """Who created / last updated the row. Deliberately no FK constraints: the
    values are audit metadata and users are soft-deleted, never removed."""

    created_by_id: Mapped[str | None] = mapped_column(ULIDType)
    updated_by_id: Mapped[str | None] = mapped_column(ULIDType)


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": version}


class SoftDeleteMixin:
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
