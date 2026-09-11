"""Authentication business logic: login, refresh rotation, logout, resets.

Security invariants (from implementation_plan.md):
* Access tokens carry identity only; permissions resolve server-side each request.
* Refresh tokens are opaque, stored SHA-256-hashed, rotated on every use.
* Reuse of a rotated/revoked token revokes the whole session family (theft).
* Failed logins and password resets share uniform responses — no user
  enumeration via timing or message text.
* Password changes invalidate every outstanding session for the account.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import AccountInactiveError, AuthenticationError
from app.core.hashing import hash_password, verify_password
from app.core.security import create_access_token, generate_refresh_token, hash_refresh_token
from app.db.types import gen_ulid
from app.modules.auth.models import (
    LoginAttempt,
    PasswordResetToken,
    RefreshToken,
)
from app.modules.iam.enums import UserStatus
from app.modules.iam.models import User
from app.modules.iam.users import repository as users_repository
from app.modules.platform_.audit.service import audit

PASSWORD_RESET_TOKEN_TTL_MINUTES = 30


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    email: str | None = None
    phone: str | None = None


async def login(
    session: AsyncSession,
    *,
    identifier: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> TokenPair:
    """Authenticate by email or phone. Uniform failures — never leaks which."""
    user = await _find_user(session, identifier)

    if user is None or user.deleted_at is not None:
        await _record_attempt(session, None, identifier, ip_address, success=False)
        raise AuthenticationError()

    if _is_locked(user):
        await _record_attempt(session, user.id, identifier, ip_address, success=False)
        raise AuthenticationError()

    if user.status != UserStatus.ACTIVE.value:
        await _record_attempt(session, user.id, identifier, ip_address, success=False)
        raise AccountInactiveError()

    password_ok = bool(user.password_hash) and verify_password(user.password_hash, password)
    if not password_ok:
        await _register_failure(session, user, identifier, ip_address)
        raise AuthenticationError()

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    await session.flush()

    await _record_attempt(session, user.id, identifier, ip_address, success=True)
    await audit(
        session, _system_ctx(ip_address),
        action="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user.id,
        organization_id=None,
        school_id=None,
    )

    return await _issue_pair(session, user, ip_address, user_agent)


async def refresh(

    session: AsyncSession,
    *,
    refresh_token: str,
    ip_address: str | None,
    user_agent: str | None,
) -> TokenPair:
    """Rotate a refresh token. Detecting reuse revokes the entire family."""
    digest = hash_refresh_token(refresh_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_digest == digest))
    if stored is None:
        raise AuthenticationError()

    if stored.revoked_at is not None or stored.rotated_at is not None:
        # Theft response must survive the request's rollback (the request ends
        # in 401), so the family revocation is committed independently.
        await _revoke_family_durable(stored.session_family_id)
        raise AuthenticationError()

    if stored.expires_at <= datetime.now(UTC):
        stored.revoked_at = datetime.now(UTC)
        await session.flush()
        raise AuthenticationError()

    user = await users_repository.get_by_id(session, stored.user_id)
    if user is None or user.deleted_at is not None:
        await _revoke_family_durable(stored.session_family_id)
        raise AuthenticationError()
    if user.status != UserStatus.ACTIVE.value:
        raise AccountInactiveError()

    stored.rotated_at = datetime.now(UTC)
    new_token, raw = _build_refresh_token(
        stored.user_id, stored.session_family_id, ip_address, user_agent
    )
    session.add(new_token)
    await session.flush()

    return TokenPair(
        access_token=create_access_token(stored.user_id),
        refresh_token=raw,
        expires_in=get_settings().access_token_expire_seconds,
        user_id=stored.user_id,
    )


async def logout(session: AsyncSession, ctx: RequestContext, *, refresh_token: str) -> None:
    digest = hash_refresh_token(refresh_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_digest == digest))
    if stored is None:
        return  # idempotent: the session is already gone

    stored.revoked_at = datetime.now(UTC)
    await session.flush()
    await audit(session, ctx, action="LOGOUT", entity_type="user", entity_id=stored.user_id)


async def request_password_reset(
    session: AsyncSession,
    *,
    identifier: str,
    ip_address: str | None,
) -> None:
    """Issue a reset token only to known, active accounts. Response is uniform."""
    user = await _find_user(session, identifier)
    if user is not None and user.status == UserStatus.ACTIVE.value:
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES),
            requested_ip=ip_address,
        )
        session.add(token)
        await session.flush()
        await audit(
            session, _system_ctx(ip_address),
            action="PASSWORD_RESET_REQUESTED",
            entity_type="user",
            entity_id=user.id,
        )


async def confirm_password_reset(
    session: AsyncSession,
    *,
    token: str,
    new_password: str,
    ip_address: str | None,
) -> None:
    digest = hash_refresh_token(token)
    stored = await session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == digest)
    )
    if stored is None or stored.consumed_at is not None or stored.expires_at <= datetime.now(UTC):
        raise AuthenticationError("This reset link is invalid or has expired.")

    user = await users_repository.get_by_id(session, stored.user_id)
    if user is None or user.deleted_at is not None:
        raise AuthenticationError("This reset link is invalid or has expired.")

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = False
    user.status = UserStatus.ACTIVE.value
    user.failed_login_count = 0
    user.locked_until = None

    stored.consumed_at = datetime.now(UTC)

    await _revoke_all_user_sessions(session, user.id)
    await session.flush()

    await audit(
        session, _system_ctx(ip_address),
        action="PASSWORD_RESET_CONFIRMED",
        entity_type="user",
        entity_id=user.id,
    )


async def change_password(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    current_password: str,
    new_password: str,
) -> None:
    user = await users_repository.get_by_id(session, ctx.user_id)
    if user is None or not user.password_hash or not verify_password(user.password_hash, current_password):
        raise AuthenticationError("The current password is incorrect.")

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = False
    user.failed_login_count = 0
    user.locked_until = None

    await _revoke_all_user_sessions(session, user.id)
    await session.flush()

    await audit(session, ctx, action="PASSWORD_CHANGED", entity_type="user", entity_id=user.id)


# =========================================================================
# Internal helpers
# =========================================================================

async def _issue_pair(
    session: AsyncSession,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> TokenPair:
    family_id = gen_ulid()
    token, raw = _build_refresh_token(user.id, family_id, ip_address, user_agent)
    session.add(token)
    await session.flush()

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        expires_in=get_settings().access_token_expire_seconds,
        user_id=user.id,
        email=user.email,
        phone=user.phone,
    )


def _build_refresh_token(
    user_id: str,
    family_id: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[RefreshToken, str]:
    raw, digest = generate_refresh_token()
    token = RefreshToken(
        user_id=user_id,
        token_digest=digest,
        session_family_id=family_id,
        expires_at=datetime.now(UTC) + timedelta(seconds=get_settings().refresh_token_expire_seconds),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return token, raw


async def _find_user(session: AsyncSession, identifier: str) -> User | None:
    if "@" in identifier:
        return await users_repository.get_by_email(session, identifier)
    return await users_repository.get_by_phone(session, identifier)


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > datetime.now(UTC)


async def _register_failure(
    session: AsyncSession,
    user: User,
    identifier: str,
    ip_address: str | None,
) -> None:
    """Increment the failed-login counter and enforce lockout.

    Runs in its own committed transaction because the login request ends in a
    401 — the request-scoped transaction is rolled back on exception and would
    otherwise discard the counter and lockout timestamp.
    """
    from app.db.session import async_session_factory

    settings = get_settings()
    async with async_session_factory() as bookkeeping, bookkeeping.begin():
        fresh = await bookkeeping.get(User, user.id)
        if fresh is None:
            return
        fresh.failed_login_count += 1
        if fresh.failed_login_count >= settings.login_max_failed_attempts:
            fresh.locked_until = datetime.now(UTC) + timedelta(
                minutes=settings.login_lockout_minutes
            )
            fresh.failed_login_count = 0
    await _record_attempt(session, user.id, identifier, ip_address, success=False)


async def _record_attempt(
    session: AsyncSession,
    user_id: str | None,
    identifier: str,
    ip_address: str | None,
    *,
    success: bool,
) -> None:
    # Committed independently: on failure the request transaction is rolled
    # back, but the attempt audit trail must persist.
    from app.db.session import async_session_factory

    async with async_session_factory() as bookkeeping, bookkeeping.begin():
        bookkeeping.add(
            LoginAttempt(
                user_id=user_id,
                email_attempted=identifier,
                ip_address=ip_address,
                success=success,
            )
        )


async def _revoke_family_durable(family_id: str) -> None:
    """Revoke every token in a session family in a committed transaction.

    Called on the theft path, where the request ends in a 401 and the
    request-scoped transaction is rolled back — the revocation must survive.
    """
    from app.db.session import async_session_factory

    async with async_session_factory() as bookkeeping, bookkeeping.begin():
        rows = list(
            (
                await bookkeeping.scalars(
                    select(RefreshToken).where(
                        RefreshToken.session_family_id == family_id
                    )
                )
            ).all()
        )
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now


async def _revoke_all_user_sessions(session: AsyncSession, user_id: str) -> None:
    rows = list(
        (await session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )).all()
    )
    now = datetime.now(UTC)
    for row in rows:
        row.revoked_at = now


def _system_ctx(ip_address: str | None) -> RequestContext:
    return RequestContext(
        user_id="",
        person_id=None,
        email=None,
        organization_id=None,
        school_id=None,
        accessible_school_ids=frozenset(),
        permissions=frozenset(),
        request_id="",
        ip_address=ip_address,
    )
