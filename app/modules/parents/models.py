"""Parent ORM models — school-scoped."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.parents.enums import ParentRelationship, ParentStatus

if TYPE_CHECKING:
    from app.modules.people.models import Person
    from app.modules.students.models import Student


class Parent(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    """A parent/guardian record linking a Person to a School."""

    __tablename__ = "parents"

    person_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    occupation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    workplace: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ParentStatus.ACTIVE.value,
        server_default=ParentStatus.ACTIVE.value,
    )

    person: Mapped["Person"] = orm_relationship(
        "Person", foreign_keys=[person_id], lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("school_id", "person_id", name="uq_parents_school_person"),
        enum_check("status", ParentStatus, "ck_parents_status"),
    )


class StudentParent(PKMixin, TimestampMixin, ActorMixin, Base):
    """A parent-to-student relationship record."""

    __tablename__ = "student_parents"

    school_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("parents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    relationship: Mapped[str] = mapped_column(String(30), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_emergency_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped["Parent"] = orm_relationship(
        "Parent", foreign_keys=[parent_id], lazy="raise"
    )
    student: Mapped["Student"] = orm_relationship(
        "Student", foreign_keys=[student_id], lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("student_id", "parent_id", name="uq_student_parent"),
        enum_check("relationship", ParentRelationship, "ck_student_parents_relationship"),
    )
