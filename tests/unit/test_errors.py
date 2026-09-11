"""Unit tests for the error envelope and exception hierarchy."""
from __future__ import annotations

from app.core.errors import (
    AccountInactiveError,
    ApiError,
    AuthenticationError,
    ConflictError,
    DuplicateError,
    ErrorCode,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    RateLimitedError,
    StaleResourceError,
    TenantContextError,
)


def test_error_codes_are_stable_strings() -> None:
    assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
    assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"


def test_api_error_defaults() -> None:
    error = ApiError("boom")
    assert error.message == "boom"
    assert error.code == ErrorCode.INTERNAL_ERROR
    assert error.details == {}


def test_http_status_codes() -> None:
    assert AuthenticationError().status_code == 401
    assert ForbiddenError().status_code == 403
    assert AccountInactiveError().status_code == 403
    assert NotFoundError().status_code == 404
    assert ConflictError().status_code == 409
    assert StaleResourceError().status_code == 409
    assert InvalidRequestError().status_code == 400
    assert RateLimitedError().status_code == 429


def test_tenant_context_error_is_forbidden() -> None:
    error = TenantContextError()
    assert isinstance(error, ForbiddenError)
    assert str(error.code) == "TENANT_CONTEXT"


def test_duplicate_error_is_conflict() -> None:
    error = DuplicateError("dup", details={"field": "email"})
    assert isinstance(error, ConflictError)
    assert error.details == {"field": "email"}


def test_rate_limited_carries_retry_after() -> None:
    error = RateLimitedError(retry_after=12)
    assert error.details["retry_after"] == 12
