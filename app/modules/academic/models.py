"""Academic foundation ORM models.

All six academic entities are school-scoped; the RLS policy filters by school_id.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.academic.enums import (
    AcademicClassStatus,
    AcademicTermStatus,
    AcademicYearStatus,
    CohortStatus,
    SubjectStatus,
    SubjectType,
)


class AcademicYear(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A school academic year, e.g. 2024-25."""

    __tablename__ = "academic_years"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AcademicYearStatus.DRAFT.value,
        server_default=AcademicYearStatus.DRAFT.value,
    )

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_academic_years_school_id_code"),
        enum_check("status", AcademicYearStatus, "status"),
        Index("ix_academic_years_school_id_is_current", "school_id", "is_current"),
    )


class AcademicTerm(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A term / semester within an academic year."""

    __tablename__ = "academic_terms"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AcademicTermStatus.ACTIVE.value,
        server_default=AcademicTermStatus.ACTIVE.value,
    )

    __table_args__ = (
        UniqueConstraint("school_id", "academic_year_id", "code", name="uq_academic_terms_school_year_code"),
        enum_check("status", AcademicTermStatus, "status"),
    )


class AcademicClass(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A class / grade level (e.g. Grade 5, Class X)."""

    __tablename__ = "academic_classes"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AcademicClassStatus.ACTIVE.value,
        server_default=AcademicClassStatus.ACTIVE.value,
    )

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_academic_classes_school_id_code"),
        enum_check("status", AcademicClassStatus, "status"),
    )


class Subject(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A subject / discipline offered by the school."""

    __tablename__ = "subjects"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    subject_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=SubjectType.CORE.value,
        server_default=SubjectType.CORE.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubjectStatus.ACTIVE.value,
        server_default=SubjectStatus.ACTIVE.value,
    )

    __table_args__ = (
        UniqueConstraint("school_id", "code", name="uq_subjects_school_id_code"),
        enum_check("subject_type", SubjectType, "subject_type"),
        enum_check("status", SubjectStatus, "status"),
    )


class ClassSubject(PKMixin, TimestampMixin, ActorMixin, Base):
    """Links a Subject to an AcademicClass for a given year range.

    No version field — this is a configuration join; conflicts are prevented
    by the unique constraint.
    """

    __tablename__ = "class_subjects"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_class_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    effective_from_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )
    effective_to_year_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "school_id", "academic_class_id", "subject_id",
            name="uq_class_subjects_school_class_subject",
        ),
        Index("ix_class_subjects_effective_from_year_id", "effective_from_year_id"),
    )


class Cohort(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A section / division of a class within a year (e.g. Grade 5 Section A)."""

    __tablename__ = "cohorts"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_class_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CohortStatus.ACTIVE.value,
        server_default=CohortStatus.ACTIVE.value,
    )

    __table_args__ = (
        UniqueConstraint(
            "school_id", "academic_year_id", "academic_class_id", "code",
            name="uq_cohorts_school_year_class_code",
        ),
        enum_check("status", CohortStatus, "status"),
    )
