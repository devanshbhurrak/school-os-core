"""Health-check endpoints (liveness + readiness).

These are registered at the app level (not under /api/v1) so that load
balancers and Kubernetes probes can reach them without an auth header.

Phase 3: readiness covers database + Redis (when configured). Cloud Run uses
`/health/ready` as its startup probe.
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
    """Readiness probe — 200 only when database (and Redis, if set) respond."""
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": str(exc)},
        ) from exc

    # A1: Redis readiness (shared rate-limit + dispatcher lock backend).
    from app.core.ratelimit import check_redis_connectivity
    from app.core.config import get_settings

    if get_settings().redis_url:
        redis_ok, detail = await check_redis_connectivity()
        checks["redis"] = "ok" if redis_ok else f"error: {detail}"
        if not redis_ok:
            raise HTTPException(
                status_code=503,
                detail={"status": "error", **checks},
            )
    else:
        checks["redis"] = "not_configured"

    return {"status": "ok", **checks}
