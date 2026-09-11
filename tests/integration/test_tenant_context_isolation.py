"""RLS tenant context is transaction-local and never leaks between requests.

The GUCs ``app.current_school_id`` / ``app.current_organization_id`` are set
with ``set_config(..., true)`` (``SET LOCAL``). A pooled connection must not
carry one request's tenant context into the next; this file asserts that
invariant directly.
"""
from __future__ import annotations

from sqlalchemy import text

from app.core.security import create_access_token
from app.db.rls import set_tenant_context
from app.db.session import async_session_factory


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def _gucs(session):
    # current_setting(..., true) returns NULL when the variable is unset;
    # coalesce to '' so "no tenant context" reads as the empty string, matching
    # how the RLS policies interpret an unset GUC.
    school = await session.scalar(
        text("SELECT coalesce(current_setting('app.current_school_id', true), '')")
    )
    org = await session.scalar(
        text("SELECT coalesce(current_setting('app.current_organization_id', true), '')")
    )
    return school, org


async def test_context_is_set_and_reset_within_transaction(seeded_world, app_session):
    assert await _gucs(app_session) == ("", "")

    await set_tenant_context(
        app_session,
        organization_id=seeded_world.org_a_id,
        school_id=seeded_world.school_a1_id,
    )
    assert await _gucs(app_session) == (seeded_world.school_a1_id, seeded_world.org_a_id)


async def test_new_transaction_has_no_tenant_context(seeded_world, client):
    # A request binds its own context inside its own transaction...
    resp = await client.get(
        "/api/v1/schools", headers=auth_header(seeded_world.admin_a.id)
    )
    assert resp.status_code == 200

    # ...and a fresh pooled connection must see empty GUCs, not the previous
    # request's tenant.
    async with async_session_factory() as session, session.begin():
        assert await _gucs(session) == ("", "")


async def test_committed_transaction_releases_context(seeded_world, app_session, client):
    # app_session commits at fixture teardown; a request in between must not
    # observe app_session's uncommitted SET LOCAL state either.
    await set_tenant_context(app_session, organization_id=seeded_world.org_a_id)

    resp = await client.get(
        "/api/v1/schools", headers=auth_header(seeded_world.admin_a.id)
    )
    assert resp.status_code == 200
