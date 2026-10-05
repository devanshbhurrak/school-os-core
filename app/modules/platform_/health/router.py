"""Health-check endpoints (liveness + readiness).

These are registered at the app level (not under /api/v1) so that load
balancers and Kubernetes probes can reach them without an auth header.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import SessionDep

router = APIRouter(tags=["Health"])


@router.get("/health", include_in_schema=False)
async def liveness() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
async def readiness(session: SessionDep = None) -> dict[str, str]:
    """Readiness probe — returns 200 only when the database is reachable."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": str(exc)},
        ) from exc
