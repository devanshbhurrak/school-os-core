"""Student ORM models — school-scoped."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.students.enums import EnrollmentStatus, EnrollmentType, GuardianRelationship, StudentStatus

if TYPE_CHECKING:
    from app.modules.academic.models import AcademicYear, Cohort
    from app.modules.people.models import Person


class Student(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A student enrollment record linking a Person to a School."""

    __tablename__ = "students"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    person_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    admission_number: Mapped[str] = mapped_column(String(50), nullable=False)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=StudentStatus.ACTIVE.value,
        server_default=StudentStatus.ACTIVE.value,
    )
    withdrawal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship for eager loading
    person: Mapped["Person"] = relationship(
        "Person", foreign_keys=[person_id], lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("school_id", "admission_number", name="uq_students_school_admission_number"),
        UniqueConstraint("school_id", "person_id", name="uq_students_school_person"),
        enum_check("status", StudentStatus, "ck_students_status"),
    )


class StudentEnrollment(PKMixin, TimestampMixin, VersionMixin, ActorMixin, Base):
    """A single enrollment of a student in a cohort for an academic year."""

    __tablename__ = "student_enrollments"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_class_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("academic_classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cohort_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    roll_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrollment_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=EnrollmentType.REGULAR.value,
        server_default=EnrollmentType.REGULAR.value,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=EnrollmentStatus.ACTIVE.value,
        server_default=EnrollmentStatus.ACTIVE.value,
    )

    # Relationships for eager loading
    student: Mapped["Student"] = relationship("Student", foreign_keys=[student_id], lazy="raise")
    cohort: Mapped["Cohort"] = relationship("Cohort", foreign_keys=[cohort_id], lazy="raise")
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", foreign_keys=[academic_year_id], lazy="raise"
    )

    __table_args__ = (
        # Partial unique indexes are defined in the migration, not here.
        # Declarative UniqueConstraints are included for documentation only:
        # the DB enforces partial indexes (WHERE status = 'ACTIVE').
        enum_check("status", EnrollmentStatus, "ck_student_enrollments_status"),
        enum_check("enrollment_type", EnrollmentType, "ck_student_enrollments_enrollment_type"),
    )


class StudentGuardian(PKMixin, TimestampMixin, ActorMixin, Base):
    """A guardian-to-student relationship record."""

    __tablename__ = "student_guardians"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    guardian_person_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(30), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_emergency_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    guardian_person: Mapped["Person"] = relationship(
        "Person", foreign_keys=[guardian_person_id], lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("student_id", "guardian_person_id", name="uq_student_guardian_person"),
        enum_check("relationship", GuardianRelationship, "ck_student_guardians_relationship"),
    )
