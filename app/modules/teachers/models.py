"""Teacher ORM models — school-scoped."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.teachers.enums import AssignmentRole, AssignmentStatus, TeacherStatus


class Teacher(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A teacher profile linking a Person to a school."""

    __tablename__ = "teachers"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    person_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    employee_number: Mapped[str | None] = mapped_column(String(50))
    designation: Mapped[str | None] = mapped_column(String(100))
    joining_date: Mapped[date | None] = mapped_column(Date)
    leaving_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TeacherStatus.ACTIVE.value,
        server_default=TeacherStatus.ACTIVE.value,
    )

    person = relationship("Person", foreign_keys=[person_id], lazy="raise")

    __table_args__ = (
        UniqueConstraint("school_id", "person_id", name="uq_teachers_school_id_person_id"),
        enum_check("status", TeacherStatus, "status"),
        # Partial unique index: employee_number must be unique per school when set
        Index(
            "uq_teachers_school_id_employee_number",
            "school_id",
            "employee_number",
            unique=True,
            postgresql_where=text("employee_number IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class TeacherAssignment(PKMixin, TimestampMixin, VersionMixin, ActorMixin, Base):
    """An assignment of a teacher to a cohort for an academic year."""

    __tablename__ = "teacher_assignments"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teacher_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cohort_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=AssignmentRole.SUBJECT_TEACHER.value,
        server_default=AssignmentRole.SUBJECT_TEACHER.value,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=AssignmentStatus.ACTIVE.value,
        server_default=AssignmentStatus.ACTIVE.value,
    )

    teacher = relationship("Teacher", foreign_keys=[teacher_id], lazy="raise")
    cohort = relationship("Cohort", foreign_keys=[cohort_id], lazy="raise")
    subject = relationship("Subject", foreign_keys=[subject_id], lazy="raise")
    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id], lazy="raise")

    __table_args__ = (
        enum_check("role", AssignmentRole, "role"),
        enum_check("status", AssignmentStatus, "status"),
        Index("ix_teacher_assignments_subject_id", "subject_id"),
    )
