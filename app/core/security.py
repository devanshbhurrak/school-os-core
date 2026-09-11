"""JWT handling and token utilities (PyJWT).

The access token carries *identity only* — `sub` (user id), `jti`, `exp`. No
roles, permissions or school ids. Permissions are resolved server-side on every
request, so revoking a membership takes effect immediately rather than at token
expiry.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AuthenticationError


def create_access_token(user_id: str, *, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes)),
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate signature + expiry and return the payload.

    Raises `AuthenticationError` for any invalid/expired/tampered token.
    """
    settings = get_settings()
    try:
        return pyjwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except pyjwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Your session has expired. Please sign in again.") from exc
    except pyjwt.InvalidTokenError as exc:
        raise AuthenticationError() from exc


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw opaque token, sha256 digest). Only the digest is stored."""
    raw = secrets.token_urlsafe(48)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, digest


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    return header[7:].strip()


def get_current_user_id(request: Request) -> str:
    """FastAPI dependency: the authenticated user's id.

    The AuthMiddleware validates the JWT and stashes the payload on
    `request.state.identity`. This dependency reads that result and returns the
    subject, raising the uniform 401 if the request was not authenticated.
    """
    identity = getattr(request.state, "identity", None)
    if not identity:
        raise AuthenticationError()
    return str(identity["sub"])


def validate_request_jwt(request: Request) -> dict[str, Any] | None:
    """Used by the middleware: decode the bearer token, or return None.

    A malformed/expired token results in no identity rather than a hard reject,
    so public endpoints still work; authenticated dependencies then raise 401.
    """
    token = _extract_bearer(request)
    if token is None:
        return None
    try:
        return decode_access_token(token)
    except AuthenticationError:
        return None
