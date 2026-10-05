"""Document request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadRequest(BaseModel):
    entity_type: str
    entity_id: str
    document_type: str
    original_filename: str
    mime_type: str
    file_size: int = Field(gt=0)


class DocumentUploadResponse(BaseModel):
    id: str
    upload_url: str
    storage_key: str


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    school_id: str
    organization_id: str
    entity_type: str
    entity_id: str
    document_type: str
    original_filename: str
    storage_key: str
    mime_type: str | None
    file_size: int | None
    checksum_sha256: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    created_by_id: str | None


class DocumentDownloadResponse(BaseModel):
    download_url: str
    filename: str


class DocumentListParams(BaseModel):
    entity_type: str | None = None
    entity_id: str | None = None
    document_type: str | None = None
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
