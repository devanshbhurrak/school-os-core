"""Error codes, exception hierarchy and FastAPI exception handlers.

Every error leaves the service in one envelope:

    {
      "error": {
        "code": "SCHOOL_NOT_FOUND",
        "message": "The requested school was not found.",
        "details": {},
        "request_id": "..."
      }
    }

Clients branch on `code`, never on `message`. No stack traces are ever leaked
to a client; internal errors are logged with full context and request_id.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger("school_os.errors")


class ErrorCode(StrEnum):
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    STALE_RESOURCE = "STALE_RESOURCE"
    RATE_LIMITED = "RATE_LIMITED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiError(Exception):
    """Base class for every error the API understands."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: ErrorCode | str = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str | ErrorCode | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code


class AuthenticationError(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.UNAUTHORIZED

    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(message)


class AccountInactiveError(ApiError):
    """Authenticated principal whose account is not active. Deliberately the
    same shape as ForbiddenError so callers cannot distinguish reasons."""

    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.ACCOUNT_INACTIVE

    def __init__(self, message: str = "This account cannot be used right now.") -> None:
        super().__init__(message)


class ForbiddenError(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.FORBIDDEN

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        *,
        code: str | ErrorCode | None = None,
    ) -> None:
        super().__init__(message, code=code)


class TenantContextError(ForbiddenError):
    """No active school / requested school not among the caller's memberships."""

    def __init__(self, message: str = "You do not have access to this school.") -> None:
        super().__init__(message, code="TENANT_CONTEXT")


class NotFoundError(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.NOT_FOUND

    def __init__(
        self, message: str = "The requested resource was not found.", *, code: str | None = None
    ) -> None:
        super().__init__(message, code=code or ErrorCode.NOT_FOUND.value)


class InvalidRequestError(ApiError):
    """Malformed query input (e.g. bad cursor or unknown sort field)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = ErrorCode.VALIDATION_ERROR

    def __init__(
        self,
        message: str = "The request is invalid.",
        *,
        code: str | ErrorCode | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class ConflictError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.CONFLICT

    def __init__(
        self,
        message: str = "The request conflicts with the current state.",
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code or ErrorCode.CONFLICT.value, details=details)


class DuplicateError(ConflictError):
    """A uniqueness constraint was violated. Details name the offending field."""

    def __init__(self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code=code, details=details)


class StaleResourceError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.STALE_RESOURCE

    def __init__(
        self,
        message: str = (
            "Someone else updated this record while you were editing it. "
            "Refresh to see the latest version, then reapply your changes."
        ),
    ) -> None:
        super().__init__(message)


class RateLimitedError(ApiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = ErrorCode.RATE_LIMITED

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        *,
        retry_after: int | None = None,
    ) -> None:
        details = {"retry_after": retry_after} if retry_after is not None else {}
        super().__init__(message, details=details)


def _error_body(request: Request, code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    from app.core.context import get_request_id

    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": get_request_id(request),
        }
    }


def _code_value(code: str | ErrorCode) -> str:
    """Emit the enum *value* (``"UNAUTHORIZED"``), not ``str(enum)`` which
    renders as ``"ErrorCode.UNAUTHORIZED"``."""
    return code.value if isinstance(code, ErrorCode) else str(code)


def register_exception_handlers(app: FastAPI) -> None:
    from app.core.context import get_request_id

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        code = _code_value(exc.code)
        if exc.status_code >= 500:
            logger.error(
                "api_error",
                exc_info=exc,
                request_id=get_request_id(request),
                code=code,
            )
        else:
            logger.warning(
                "api_error",
                request_id=get_request_id(request),
                code=code,
                message=exc.message,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, Any] = {"fields": []}
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"] if part != "body")
            details["fields"].append(
                {
                    "field": loc,
                    "message": error["msg"],
                    "type": error.get("type"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                request,
                ErrorCode.VALIDATION_ERROR.value,
                "The request payload is invalid.",
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED.value,
            status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN.value,
            status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND.value,
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMITED.value,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR.value)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, code, message, {}),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_error",
            exc_info=exc,
            request_id=get_request_id(request),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                request,
                ErrorCode.INTERNAL_ERROR.value,
                "An unexpected error occurred.",
                {},
            ),
        )
