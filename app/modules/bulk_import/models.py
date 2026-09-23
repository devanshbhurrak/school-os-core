"""ImportJob ORM model — school-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, TimestampMixin
from app.db.types import ULIDType, enum_check
from app.modules.bulk_import.enums import ImportJobStatus, ImportResourceType


class ImportJob(PKMixin, TimestampMixin, ActorMixin, Base):
    """Tracks a bulk CSV import operation."""

    __tablename__ = "import_jobs"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ImportJobStatus.PENDING.value,
        server_default=ImportJobStatus.PENDING.value,
    )
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_summary: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        enum_check("resource_type", ImportResourceType, "ck_import_jobs_resource_type"),
        enum_check("status", ImportJobStatus, "ck_import_jobs_status"),
    )
