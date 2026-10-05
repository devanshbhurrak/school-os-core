"""Export job ORM model — school-scoped."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, TimestampMixin
from app.db.types import ULIDType, enum_check
from app.modules.reports.enums import ExportJobStatus, ReportType


class ExportJob(PKMixin, TimestampMixin, ActorMixin, Base):
    """A CSV export job record."""

    __tablename__ = "export_jobs"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ExportJobStatus.PENDING.value,
        server_default=ExportJobStatus.PENDING.value,
    )
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_export_jobs_school_created", "school_id", "created_by_id", "created_at"),
        enum_check("report_type", ReportType, "ck_export_jobs_report_type"),
        enum_check("status", ExportJobStatus, "ck_export_jobs_status"),
    )
