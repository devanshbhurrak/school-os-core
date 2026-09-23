"""Timetable ORM models — school-scoped."""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.timetables.enums import DayOfWeek, PeriodType, TimetableSlotStatus


class PeriodDefinition(PKMixin, TimestampMixin, ActorMixin, Base):
    """A school-level template slot in a day's schedule for an academic year."""

    __tablename__ = "period_definitions"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, default=PeriodType.LESSON.value)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "school_id", "academic_year_id", "name",
            name="uq_period_def_school_year_name",
        ),
        enum_check("period_type", PeriodType, "period_type"),
    )


class TimetableSlot(PKMixin, TimestampMixin, VersionMixin, ActorMixin, Base):
    """Assignment of teacher+subject to a cohort for a period on a day."""

    __tablename__ = "timetable_slots"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    cohort_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_definition_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("period_definitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TimetableSlotStatus.ACTIVE.value,
        server_default=TimetableSlotStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    teacher = relationship("Teacher", foreign_keys=[teacher_id], lazy="raise")
    subject = relationship("Subject", foreign_keys=[subject_id], lazy="raise")
    cohort = relationship("Cohort", foreign_keys=[cohort_id], lazy="raise")
    period_definition = relationship("PeriodDefinition", foreign_keys=[period_definition_id], lazy="raise")

    __table_args__ = (
        UniqueConstraint(
            "cohort_id", "period_definition_id", "day_of_week", "effective_from",
            name="uq_slot_cohort_period_day_date",
        ),
        enum_check("day_of_week", DayOfWeek, "day_of_week"),
        enum_check("status", TimetableSlotStatus, "status"),
        Index("ix_timetable_slots_teacher_id_day_of_week", "teacher_id", "day_of_week"),
    )
