"""IAM persistence model — the load-bearing part of the schema.

This shape is what makes every future module cheap, and it encodes the four
separations from PRD §9:

1. **Person vs User** — a person is a human on record; a user is a way to sign
   in. A teacher with no login and a student who never gets an account are
   normal cases, not special cases.
2. **User vs Membership** — a user is not "in" a school. A membership grants a
   user access to one school (or, with `school_id` NULL, a whole organization)
   for a period of time.
3. **Membership vs Role** — roles hang off the membership, not the user, so the
   same person can be a Teacher at School A and a Principal at School B.
4. **Role vs Permission** — roles are tenant-editable groupings; permissions are
   code-declared capabilities mirrored to the `permissions` table by
   `scripts/sync_permissions.py`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.permissions import DataScope
from app.db.base import Base
from app.db.mixins import (
    ActorMixin,
    PKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
)
from app.db.types import ULIDType, enum_check
from app.modules.iam.enums import (
    MembershipStatus,
    OrganizationStatus,
    RoleScopeLevel,
    SchoolStatus,
    UserStatus,
)


# =========================================================================
# Tenant roots
# =========================================================================
class Organization(PKMixin, TimestampMixin, VersionMixin, ActorMixin, SoftDeleteMixin, Base):
    """The customer: a single school or a group that owns several.

    Every tenant-owned row ultimately hangs off this. A single independent
    school is modelled as an organization with exactly one school — growing into
    a group later is a data change, not a migration.
    """

    __tablename__ = "organizations"

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OrganizationStatus.TRIAL.value,
        server_default=OrganizationStatus.TRIAL.value,
    )

    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Asia/Kolkata")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, server_default="en-IN")

    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(24))

    # Plan/entitlement hook (PRD §59). Feature availability always flows through
    # this, never a hard-coded True.
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False, server_default="foundation")
    entitlements: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Reserved for future region/grouping tiers.
    parent_organization_id: Mapped[str | None] = mapped_column(ULIDType)

    __table_args__ = (
        UniqueConstraint("code", name="uq_organizations_code"),
        enum_check("status", OrganizationStatus, "status"),
        Index("ix_organizations_status", "status"),
    )


class School(PKMixin, TimestampMixin, VersionMixin, ActorMixin, SoftDeleteMixin, Base):
    """One operational campus.

    Future Region / Campus / Branch tiers slot in via `parent_school_id` and
    `hierarchy_path` without moving any foreign keys.
    """

    __tablename__ = "schools"

    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SchoolStatus.SETUP.value,
        server_default=SchoolStatus.SETUP.value,
    )

    # Reserved for the Region/Campus/Branch expansion. Unused in V1.
    parent_school_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT")
    )
    hierarchy_path: Mapped[str | None] = mapped_column(Text)

    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Asia/Kolkata")
    locale: Mapped[str] = mapped_column(String(16), nullable=False, server_default="en-IN")

    board: Mapped[str | None] = mapped_column(String(40))  # CBSE / ICSE / State
    affiliation_number: Mapped[str | None] = mapped_column(String(60))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(24))
    address_id: Mapped[str | None] = mapped_column(
        ULIDType,
        ForeignKey("addresses.id", ondelete="SET NULL", use_alter=True, name="fk_schools_address_id_addresses"),
    )

    # Per-school configuration: working days, attendance session types, etc.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_schools_organization_id_code"),
        enum_check("status", SchoolStatus, "status"),
        Index("ix_schools_status", "status"),
    )


# =========================================================================
# Identity
# =========================================================================
class User(PKMixin, TimestampMixin, VersionMixin, SoftDeleteMixin, Base):
    """A login credential holder.

    Intentionally NOT tenant-scoped: tenancy comes from memberships. This is
    what lets one account serve a teacher who also has a child at a sister
    school, without duplicate profiles or a second password.
    """

    __tablename__ = "users"

    # Nullable because a platform/support account may not correspond to a
    # person record inside any customer organization. use_alter breaks the
    # users <-> persons cycle (persons.created_by_id points back at users).
    person_id: Mapped[str | None] = mapped_column(
        ULIDType,
        ForeignKey(
            "persons.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_users_person_id_persons",
        ),
        index=True,
    )

    email: Mapped[str | None] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Many Indian parents have a phone but no email, so either may be the login
    # identifier — but at least one must exist (see CHECK).
    phone: Mapped[str | None] = mapped_column(String(24))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UserStatus.INVITED.value,
        server_default=UserStatus.INVITED.value,
    )
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Bumped whenever roles or memberships change, so cached permission sets can
    # be invalidated precisely (PRD §110). Reserved for Milestone 7.
    permissions_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", lazy="selectin", foreign_keys="Membership.user_id"
    )

    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="contact_present"),
        enum_check("status", UserStatus, "status"),
        Index("ix_users_status", "status"),
        Index("ix_users_phone", "phone"),
        # Functional uniqueness for login identifiers. Partial indexes so users
        # who sign in by phone only (never have an email) don't collide on NULL.
        Index(
            "uq_users_email_lower",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("email IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index(
            "uq_users_phone_active",
            "phone",
            unique=True,
            postgresql_where=text("phone IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class Membership(PKMixin, TimestampMixin, VersionMixin, ActorMixin, Base):
    """A user's access to one school, or (school_id NULL) to a whole org.

    Time-bounded on purpose: a substitute teacher engaged for one term is a
    membership with an end date, not a row that is deleted later and loses the
    record that it existed.
    """

    __tablename__ = "memberships"

    user_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # NULL = organization-wide membership spanning every school in the org.
    school_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("schools.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MembershipStatus.ACTIVE.value,
        server_default=MembershipStatus.ACTIVE.value,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])
    role_links: Mapped[list[MembershipRole]] = relationship(
        back_populates="membership", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def role_codes(self) -> list[str]:
        return [link.role.code for link in self.role_links if link.role is not None]

    __table_args__ = (
        UniqueConstraint(
            "user_id", "organization_id", "school_id",
            name="uq_memberships_user_id_organization_id_school_id",
            postgresql_nulls_not_distinct=True,
        ),
        enum_check("status", MembershipStatus, "status"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="date_order",
        ),
        Index("ix_memberships_status", "status"),
    )


# =========================================================================
# Access control
# =========================================================================
class Permission(PKMixin, TimestampMixin, Base):
    """Mirror of the code-declared permission registry.

    Rows are synced from `app.core.permissions.registry`, never hand-written.
    They exist so roles can reference capabilities by foreign key and an admin
    UI can list them without importing Python.
    """

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (UniqueConstraint("code", name="uq_permissions_code"),)


class Role(PKMixin, TimestampMixin, VersionMixin, ActorMixin, SoftDeleteMixin, Base):
    """A named bundle of permissions plus a data scope.

    `organization_id` NULL marks a system role shipped with the product. System
    roles are immutable for tenants, so an upgrade can add a permission to
    TEACHER everywhere without merging per-tenant edits.
    """

    __tablename__ = "roles"

    organization_id: Mapped[str | None] = mapped_column(
        ULIDType, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(400))

    scope_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RoleScopeLevel.SCHOOL.value,
        server_default=RoleScopeLevel.SCHOOL.value,
    )
    # Row-visibility tier granted by this role (see core.permissions.DataScope).
    data_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DataScope.SCHOOL.value,
        server_default=DataScope.SCHOOL.value,
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    permission_links: Mapped[list[RolePermission]] = relationship(
        back_populates="role", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code",
            name="uq_roles_organization_id_code",
            postgresql_nulls_not_distinct=True,
        ),
        enum_check("scope_level", RoleScopeLevel, "scope_level"),
        enum_check("data_scope", DataScope, "data_scope"),
    )


class RolePermission(PKMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional per-permission override of the role's data scope.
    data_scope: Mapped[str | None] = mapped_column(String(20))

    role: Mapped[Role] = relationship(back_populates="permission_links")
    permission: Mapped[Permission] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_id_permission_id"),
    )


class MembershipRole(PKMixin, TimestampMixin, ActorMixin, Base):
    """Grants a role within one membership.

    Roles attach here rather than to the user so the same person can hold
    different roles at different schools (PRD §12).
    """

    __tablename__ = "membership_roles"

    membership_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Optional per-grant override of the role's data scope.
    data_scope: Mapped[str | None] = mapped_column(String(20))

    membership: Mapped[Membership] = relationship(back_populates="role_links")
    role: Mapped[Role] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("membership_id", "role_id", name="uq_membership_roles_membership_id_role_id"),
    )
