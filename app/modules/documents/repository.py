"""Document data access — school-scoped."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import CursorPage, CursorParams
from app.db.repository import paginate_cursor
from app.modules.documents.enums import DocumentStatus
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentListParams


async def get_by_id(
    session: AsyncSession, school_id: str, document_id: str, organization_id: str | None = None
) -> Document | None:
    stmt = select(Document).where(
        Document.id == document_id,
        Document.school_id == school_id,
        Document.deleted_at.is_(None),
    )
    if organization_id is not None:
        stmt = stmt.where(Document.organization_id == organization_id)
    return (await session.scalars(stmt)).first()


async def list_documents(
    session: AsyncSession,
    school_id: str,
    params: DocumentListParams,
    organization_id: str | None = None,
) -> CursorPage[Document]:
    stmt = select(Document).where(
        Document.school_id == school_id,
        Document.status == DocumentStatus.CONFIRMED.value,
        Document.deleted_at.is_(None),
    )
    if organization_id is not None:
        stmt = stmt.where(Document.organization_id == organization_id)
    if params.entity_type is not None:
        stmt = stmt.where(Document.entity_type == params.entity_type)
    if params.entity_id is not None:
        stmt = stmt.where(Document.entity_id == params.entity_id)
    if params.document_type is not None:
        stmt = stmt.where(Document.document_type == params.document_type)

    cursor_params = CursorParams(limit=params.limit, cursor=params.cursor)
    return await paginate_cursor(session, stmt, cursor_params, model=Document)


async def create(session: AsyncSession, doc: Document) -> Document:
    session.add(doc)
    await session.flush()
    return doc
