"""Application factory: middleware, error envelope, health checks, routes."""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import limiter
from app.modules.platform_.health.router import router as health_router

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
    )

    # --- slowapi rate-limit state & exception handler ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-School-ID", "X-Request-ID"],
    )

    register_exception_handlers(app)

    # --- Prometheus metrics (exposes /metrics) ---
    setup_metrics(app)

    # --- Health endpoints at root level (no /api/v1 prefix) ---
    app.include_router(health_router)

    # --- API routes ---
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
