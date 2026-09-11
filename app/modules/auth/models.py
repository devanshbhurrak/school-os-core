"""Auth persistence: refresh-token families, login attempts, reset grants.

Refresh tokens are opaque and stored as SHA-256 digests only — a database leak
yields no usable sessions. Reuse of a rotated token is treated as theft and
revokes the whole session family (rotation-on-every-use).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import PKMixin, TimestampMixin
from app.db.types import ULIDType


class RefreshToken(PKMixin, TimestampMixin, Base):
    """One issued refresh token within a session family."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    session_family_id: Mapped[str] = mapped_column(ULIDType, nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Security-events context, never used for authorization decisions.
    user_agent: Mapped[str | None] = mapped_column(String(400))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (
        UniqueConstraint("token_digest", name="uq_refresh_tokens_token_digest"),
        Index("ix_refresh_tokens_user_id_revoked_at", "user_id", "revoked_at"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


class LoginAttempt(PKMixin, Base):
    """One authentication attempt, success or failure, for audit/analysis."""

    __tablename__ = "login_attempts"

    user_id: Mapped[str | None] = mapped_column(ULIDType)  # NULL when email unknown
    email_attempted: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_login_attempts_email_attempted_attempted_at", "email_attempted", "attempted_at"),
        Index("ix_login_attempts_ip_attempted_at", "ip_address", "attempted_at"),
    )


class PasswordResetToken(PKMixin, TimestampMixin, Base):
    """Single-use, hashed, short-lived password reset grant."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[str] = mapped_column(
        ULIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_ip: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
