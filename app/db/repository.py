"""Repository support utilities.

The plan mandates *explicit* repositories: tenant filters are written out in
each module's repository so a reader can see exactly what scope is applied. No
magic base class injects filters here. What these helpers do provide is the
boring, error-prone parts: keyset pagination, offset pagination, and defensive
not-found lookups.
"""
from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRequestError, NotFoundError
from app.core.pagination import (
    CursorPage,
    CursorParams,
    OffsetPage,
    OffsetParams,
    decode_cursor,
    encode_cursor,
)

ModelT = TypeVar("ModelT")


async def paginate_cursor(
    session: AsyncSession,
    stmt: Select[tuple[ModelT]],
    params: CursorParams,
    *,
    model: type[ModelT],
) -> CursorPage[ModelT]:
    """Keyset pagination over the `(created_at, id)` tuple. Stable under inserts."""
    if params.cursor:
        try:
            created_at, row_id = decode_cursor(params.cursor)
        except ValueError as exc:
            raise InvalidRequestError("Malformed pagination cursor.") from exc
        stmt = stmt.where(tuple_(model.created_at, model.id) < (created_at, row_id))

    stmt = stmt.order_by(model.created_at.desc(), model.id.desc()).limit(params.limit + 1)
    rows = list((await session.scalars(stmt)).all())

    has_more = len(rows) > params.limit
    items = rows[: params.limit]
    next_cursor = None
    if has_more and items:
        next_cursor = encode_cursor(items[-1].created_at, items[-1].id)
    return CursorPage[ModelT](items=items, next_cursor=next_cursor, has_more=has_more)


async def paginate_offset(
    session: AsyncSession,
    stmt: Select[tuple[ModelT]],
    params: OffsetParams,
    *,
    model: type[ModelT],
    with_total: bool = False,
) -> OffsetPage[ModelT]:
    total: int | None = None
    if with_total:
        total = await _count(session, stmt)
    stmt = stmt.order_by(model.created_at.desc(), model.id.desc()).limit(params.page_size).offset(
        params.offset
    )
    rows = list((await session.scalars(stmt)).all())
    return OffsetPage[ModelT](
        items=rows,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


async def _count(session: AsyncSession, stmt: Select[Any]) -> int:
    subq = stmt.order_by(None).subquery()
    value = await session.scalar(select(func.count()).select_from(subq))
    return int(value or 0)


async def get_or_404(
    session: AsyncSession,
    stmt: Select[tuple[ModelT]],
    *,
    label: str,
    include_archived: bool = False,
) -> ModelT:
    """Execute a fully-scoped statement and raise a domain-specific 404 if empty.

    A row belonging to another tenant is genuinely invisible here, so this is a
    real 404 and not an information leak.
    """
    result = await session.scalars(stmt)
    instance = result.first()
    if instance is None:
        raise NotFoundError(
            f"The {label} was not found.",
            code=f"{label.upper().replace(' ', '_')}_NOT_FOUND",
        )
    if not include_archived and getattr(instance, "archived_at", None) is not None:
        raise NotFoundError(
            f"The {label} was not found.",
            code=f"{label.upper().replace(' ', '_')}_NOT_FOUND",
        )
    return instance
