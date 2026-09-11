"""Tenant isolation at both the API and the RLS layer.

The API tests assert observable behaviour; the direct RLS tests assert that a
hand-written query which forgets its tenant filter returns zero rows — the
"last line of defence" from implementation_plan.md.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.rls import set_tenant_context
from app.db.types import gen_ulid
from app.modules.iam.models import School


def auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ---------------------------------------------------------------------------
# RLS layer: direct queries through the RLS-enforced app session.
# ---------------------------------------------------------------------------


async def test_rls_hides_other_org_rows(seeded_world, app_session):
    await set_tenant_context(app_session, organization_id=seeded_world.org_a_id)

    other = (
        await app_session.scalars(
            select(School).where(School.organization_id == seeded_world.org_b_id)
        )
    ).all()
    assert other == []

    own = (
        await app_session.scalars(
            select(School).where(School.organization_id == seeded_world.org_a_id)
        )
    ).all()
    assert {s.id for s in own} == {seeded_world.school_a1_id, seeded_world.school_a2_id}


async def test_rls_blocks_cross_tenant_insert(seeded_world, app_session):
    # RLS rejects a violating INSERT with an asyncpg InsufficientPrivilegeError,
    # which SQLAlchemy surfaces as a ProgrammingError (not an IntegrityError).
    from sqlalchemy.exc import ProgrammingError

    try:
        async with app_session.begin_nested():
            await set_tenant_context(app_session, organization_id=seeded_world.org_a_id)
            app_session.add(
                School(
                    id=gen_ulid(),
                    organization_id=seeded_world.org_b_id,
                    code="rogue",
                    name="Rogue School",
                )
            )
            await app_session.flush()
    except (IntegrityError, ProgrammingError):
        pass
    else:
        pytest.fail("cross-tenant insert was not blocked by RLS")


# ---------------------------------------------------------------------------
# API layer.
# ---------------------------------------------------------------------------


async def test_cross_tenant_school_is_404(client, seeded_world):
    resp = await client.get(
        f"/api/v1/schools/{seeded_world.school_b1_id}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SCHOOL_NOT_FOUND"


async def test_unapproved_school_header_is_403(client, seeded_world):
    resp = await client.get(
        f"/api/v1/schools/{seeded_world.school_a1_id}",
        headers={**auth_header(seeded_world.admin_a.id), "X-School-ID": seeded_world.school_b1_id},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_CONTEXT"


async def test_cross_tenant_organization_is_404(client, seeded_world):
    resp = await client.get(
        f"/api/v1/organizations/{seeded_world.org_b_id}",
        headers=auth_header(seeded_world.admin_a.id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


async def test_admin_b_cannot_read_school_a(client, seeded_world):
    resp = await client.get(
        f"/api/v1/schools/{seeded_world.school_a1_id}",
        headers=auth_header(seeded_world.admin_b.id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SCHOOL_NOT_FOUND"
