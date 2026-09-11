"""ASGI middleware: request correlation, access logging, JWT validation.

`RequestContextMiddleware` generates/binds a `request_id`, validates any Bearer
token (stashing the identity on `request.state.identity` — dependencies decide
authorization), and emits one structured access log line per request.
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import validate_request_jwt

logger = structlog.get_logger("school_os.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        identity = validate_request_jwt(request)
        request.state.identity = identity
        if identity:
            structlog.contextvars.bind_contextvars(user_id=identity["sub"])

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 1),
        )
        return response
