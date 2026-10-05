"""Document ORM models — school-scoped."""
from __future__ import annotations

from sqlalchemy import BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import ActorMixin, PKMixin, SoftDeleteMixin, TimestampMixin
from app.db.types import ULIDType, enum_check
from app.modules.documents.enums import DocumentEntityType, DocumentStatus, DocumentType


class Document(PKMixin, TimestampMixin, SoftDeleteMixin, ActorMixin, Base):
    """A document (file) attached to a school-scoped entity."""

    __tablename__ = "documents"

    school_id: Mapped[str] = mapped_column(ULIDType, nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(ULIDType, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(ULIDType, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=DocumentStatus.PENDING_UPLOAD.value,
        server_default=DocumentStatus.PENDING_UPLOAD.value,
    )

    __table_args__ = (
        Index("ix_documents_entity", "entity_type", "entity_id"),
        Index("ix_documents_school_status", "school_id", "status"),
        enum_check("entity_type", DocumentEntityType, "ck_documents_entity_type"),
        enum_check("document_type", DocumentType, "ck_documents_document_type"),
        enum_check("status", DocumentStatus, "ck_documents_status"),
    )
