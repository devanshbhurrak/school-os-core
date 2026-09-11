"""Authorization guard: permission x data scope.

`require()` is a FastAPI dependency factory. It validates the permission code
against the registry *at import time* — a route referencing an unregistered code
crashes the process at startup, not silently 403s in production.

Scope resolution: when a user holds several roles the strongest scope wins
(OWN < ASSIGNED < SCHOOL < ORGANIZATION < PLATFORM). A required minimum scope
further narrows row access.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.core.context import RequestContext, get_context
from app.core.errors import ForbiddenError
from app.core.permissions import DataScope, Permission, registry


def require(permission: Permission, scope: DataScope | None = None) -> Callable:
    """Return a dependency that guards a route with `permission [at scope]`."""
    registry.require_registered(permission.code)  # fails fast at import time

    async def _guard(ctx: RequestContext = Depends(get_context)) -> RequestContext:
        effective = ctx.effective_scope_for(permission.code)
        if effective is None:
            raise ForbiddenError(f"Missing permission: {permission.code}")
        if scope is not None and effective.strength() < scope.strength():
            raise ForbiddenError(f"Insufficient scope for: {permission.code}")
        return ctx

    return _guard


def require_authenticated(ctx: RequestContext = Depends(get_context)) -> RequestContext:
    """Guard for endpoints that need an authenticated principal but no single
    permission (e.g. `/auth/me`)."""
    if not ctx.user_id:
        from app.core.errors import AuthenticationError

        raise AuthenticationError()
    return ctx
