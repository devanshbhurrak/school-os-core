"""Attendance ORM models — school-scoped."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.attendance.enums import AttendanceSessionStatus, AttendanceStatus

if TYPE_CHECKING:
    from app.modules.attendance.models import AttendanceRecord


class AttendanceSession(PKMixin, TimestampMixin, VersionMixin, ActorMixin, Base):
    """One roll-call event per cohort per date."""

    __tablename__ = "attendance_sessions"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    cohort_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AttendanceSessionStatus.DRAFT.value,
        server_default=AttendanceSessionStatus.DRAFT.value,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="session", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("cohort_id", "session_date", name="uq_attendance_session_cohort_date"),
        enum_check("status", AttendanceSessionStatus, "ck_attendance_sessions_status"),
    )


class AttendanceRecord(PKMixin, TimestampMixin, ActorMixin, Base):
    """One attendance mark per student per session."""

    __tablename__ = "attendance_records"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrollment_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("student_enrollments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AttendanceStatus.PRESENT.value,
        server_default=AttendanceStatus.PRESENT.value,
    )
    arrived_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession", back_populates="records", lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("session_id", "enrollment_id", name="uq_record_session_enrollment"),
        enum_check("status", AttendanceStatus, "ck_attendance_records_status"),
    )
