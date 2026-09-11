"""Async engine, session factory and the request-scoped `get_db` dependency.

Transaction discipline
----------------------
`get_db` wraps the yield in `session.begin()`. Every request therefore runs in
an explicit transaction:

* `SET LOCAL` (used for RLS tenant context) only takes effect inside a
  BEGIN/COMMIT block — outside one it is silently ignored.
* The transaction auto-commits on a clean exit and auto-rolls-back on
  exception; no repository or service ever calls `commit()`.

`expire_on_commit=False` keeps loaded attributes accessible after commit
(accessing an expired attribute in async triggers a lazy load that raises
`MissingGreenlet`). `autoflush=False` makes flushes explicit.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session bound to a single transaction for the request lifetime."""
    async with async_session_factory() as session, session.begin():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]
