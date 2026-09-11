"""Auth routes: public login/refresh/reset, authenticated logout/me/change."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.core.authz import require_authenticated
from app.core.config import get_settings
from app.core.context import get_client_ip, get_request_id
from app.core.errors import RateLimitedError
from app.core.ratelimit import (
    login_limiter,
    login_rate_limit_key,
    password_reset_limiter,
    password_reset_rate_limit_key,
)
from app.db.session import SessionDep
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RefreshResponse,
    UserBrief,
)
from app.modules.iam.users import repository as users_repository

router = APIRouter(prefix="/auth", tags=["auth"])


class ResetAccepted(BaseModel):
    message: str = "If an account exists for this identifier, a reset link has been sent."
    request_id: str = ""


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    session: SessionDep = None,
):
    settings = get_settings()
    ip = get_client_ip(request)
    allowed, retry_after = login_limiter.allow(
        login_rate_limit_key(ip), settings.login_rate_limit_per_minute, 60
    )
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)

    pair = await service.login(
        session,
        identifier=data.identifier,
        password=data.password,
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    return LoginResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=UserBrief(id=pair.user_id, email=pair.email, phone=pair.phone),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    data: RefreshRequest,
    request: Request,
    session: SessionDep = None,
):
    pair = await service.refresh(
        session,
        refresh_token=data.refresh_token,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return RefreshResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    ctx=Depends(require_authenticated),
    session: SessionDep = None,
):
    await service.logout(session, ctx, refresh_token=data.refresh_token)


@router.post("/password-reset", response_model=ResetAccepted, status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    session: SessionDep = None,
):
    settings = get_settings()
    ip = get_client_ip(request)
    allowed, retry_after = password_reset_limiter.allow(
        password_reset_rate_limit_key(ip), settings.password_reset_rate_limit_per_hour, 3600
    )
    if not allowed:
        raise RateLimitedError(retry_after=retry_after)

    await service.request_password_reset(
        session, identifier=data.identifier, ip_address=ip
    )
    return ResetAccepted(request_id=get_request_id(request))


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    request: Request,
    session: SessionDep = None,
):
    await service.confirm_password_reset(
        session,
        token=data.token,
        new_password=data.new_password,
        ip_address=get_client_ip(request),
    )


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChange,
    ctx=Depends(require_authenticated),
    session: SessionDep = None,
):
    await service.change_password(
        session, ctx, current_password=data.current_password, new_password=data.new_password
    )


@router.get("/me", response_model=MeResponse)
async def me(
    ctx=Depends(require_authenticated),
    session: SessionDep = None,
):
    user = await users_repository.get_by_id(session, ctx.user_id)
    return MeResponse(
        user_id=ctx.user_id,
        person_id=ctx.person_id,
        email=ctx.email or (user.email if user else None),
        phone=user.phone if user else None,
        is_platform_admin=ctx.is_platform_admin,
        organization_id=ctx.organization_id,
        school_id=ctx.school_id,
        role_codes=sorted(ctx.role_codes),
        permissions=sorted(ctx.permissions),
        must_change_password=bool(user.must_change_password) if user else False,
    )
