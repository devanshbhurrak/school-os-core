"""People models: shared identity, reusable address and contact records.

`Person` is organization-scoped, not school-scoped (PRD §18, ARCHITECTURE §3).
A student transferred between schools in the same organization keeps one
identity and one history; the transfer is a new enrollment, not a duplicate
person. Addresses and contacts are polymorphic (`entity_type`/`entity_id`) so
schools, persons and future profiles all reuse them without per-domain tables.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin, VersionMixin
from app.db.types import ULIDType, enum_check
from app.modules.people.enums import AddressType, ContactType, PersonStatus


class Address(PKMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "addresses"

    # Polymorphic owner: "SCHOOL", "PERSON", ...
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[str] = mapped_column(ULIDType, nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )

    address_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default=AddressType.RESIDENTIAL.value,
        server_default=AddressType.RESIDENTIAL.value,
    )
    line1: Mapped[str | None] = mapped_column(String(200))
    line2: Mapped[str | None] = mapped_column(String(200))
    landmark: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, server_default="IN")
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        enum_check("address_type", AddressType, "address_type"),
        Index("ix_addresses_entity", "entity_type", "entity_id"),
        Index("ix_addresses_organization_id", "organization_id"),
    )


class Person(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, ActorMixin, Base):
    __tablename__ = "persons"

    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date, index=True)
    gender: Mapped[str | None] = mapped_column(String(24))
    blood_group: Mapped[str | None] = mapped_column(String(8))
    nationality: Mapped[str | None] = mapped_column(String(60))

    primary_phone: Mapped[str | None] = mapped_column(String(24), index=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), index=True)

    address_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("addresses.id", ondelete="SET NULL")
    )
    # Documents module arrives in a later milestone; column reserved.
    photo_document_id: Mapped[str | None] = mapped_column(ULIDType)

    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=PersonStatus.ACTIVE.value,
        server_default=PersonStatus.ACTIVE.value,
    )
    merged_into_person_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("persons.id", ondelete="SET NULL")
    )
    custom_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        enum_check("status", PersonStatus, "status"),
        CheckConstraint(
            "merged_into_person_id IS NULL OR merged_into_person_id <> id",
            name="merge_not_self",
        ),
        Index("ix_persons_organization_id_last_name", "organization_id", "last_name"),
        # Gin trigram over the full name for duplicate detection / search.
        Index(
            "ix_persons_name_trgm",
            text(
                "(coalesce(first_name,'') || ' ' || coalesce(middle_name,'') || ' ' || "
                "coalesce(last_name,'')) gin_trgm_ops"
            ),
            postgresql_using="gin",
        ),
    )


class Contact(PKMixin, TimestampMixin, Base):
    __tablename__ = "contacts"

    # Polymorphic owner: "PERSON", "SCHOOL", ...
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[str] = mapped_column(ULIDType, nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )

    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(60))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        enum_check("contact_type", ContactType, "contact_type"),
        UniqueConstraint(
            "entity_type", "entity_id", "contact_type", "value",
            name="uq_contacts_entity_type_entity_id_contact_type_value",
        ),
        Index("ix_contacts_entity", "entity_type", "entity_id"),
        Index("ix_contacts_organization_id", "organization_id"),
    )
