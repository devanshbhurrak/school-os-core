"""File authorization tests (Phase 3, C1): document upload/download access control.

* Upload URL generation requires the document-create permission.
* Download URLs require entity access — cross-school access returns 404
  (indistinguishable from missing, so no tenant info leaks).
* Oversized uploads and disallowed MIME types are rejected at request time.
"""
from __future__ import annotations

from app.core.security import create_access_token


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def school_auth(user_id: str, school_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-School-ID": school_id,
    }


def _upload_payload(entity_id: str = "entity-001") -> dict:
    return {
        "entity_type": "student",
        "entity_id": entity_id,
        "document_type": "REPORT_CARD",
        "original_filename": "report.pdf",
        "mime_type": "application/pdf",
        "file_size": 1024,
    }


async def test_upload_url_requires_permission(seeded_world, client):
    """A user with no memberships (no permissions) cannot mint upload URLs."""
    resp = await client.post(
        "/api/v1/documents/upload-url",
        json=_upload_payload(),
        headers=school_auth(seeded_world.lone_user.id, seeded_world.school_a1_id),
    )
    # Lone user has no membership in the school → 403 via tenant context,
    # or 403 via missing permission. Either way, denied.
    assert resp.status_code in (401, 403)


async def test_upload_url_requires_authentication(seeded_world, client):  # noqa: ARG001
    resp = await client.post("/api/v1/documents/upload-url", json=_upload_payload())
    assert resp.status_code == 401


async def test_cross_school_document_download_rejected(seeded_world, client):
    """A document created in school A is invisible from school B's context."""
    create = await client.post(
        "/api/v1/documents/upload-url",
        json=_upload_payload(),
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert create.status_code == 201, create.text
    doc_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/documents/{doc_id}/download-url",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


async def test_cross_school_document_list_isolated(seeded_world, client):
    """School B's document list never contains school A's documents."""
    create = await client.post(
        "/api/v1/documents/upload-url",
        json=_upload_payload(entity_id="entity-iso-1"),
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert create.status_code == 201, create.text
    doc_id = create.json()["id"]

    listing = await client.get(
        "/api/v1/documents",
        headers=school_auth(seeded_world.school_admin_b1.id, seeded_world.school_b1_id),
    )
    assert listing.status_code == 200
    assert doc_id not in {d["id"] for d in listing.json()["items"]}


async def test_oversized_upload_rejected(seeded_world, client):
    """A declared file size above the cap is rejected (413 or 422)."""
    payload = _upload_payload()
    payload["file_size"] = 500 * 1024 * 1024  # 500 MiB > 50 MiB default cap
    resp = await client.post(
        "/api/v1/documents/upload-url",
        json=payload,
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code in (413, 422)


async def test_disallowed_mime_type_rejected(seeded_world, client):
    """An executable MIME type is rejected even with a benign filename."""
    payload = _upload_payload()
    payload["mime_type"] = "application/x-msdownload"
    payload["original_filename"] = "report.pdf"
    resp = await client.post(
        "/api/v1/documents/upload-url",
        json=payload,
        headers=school_auth(seeded_world.school_admin_a1.id, seeded_world.school_a1_id),
    )
    assert resp.status_code in (400, 422)
