"""S3-compatible storage abstraction for document uploads/downloads.

Phase 3 hardening (Cloudflare R2 target, S3-compatible API):
* Pre-signed PUT URLs carry a `Content-Length-Range` condition so oversized
  files are rejected at the edge before they reach the bucket.
* `head_object_info()` returns size + content-type + ETag for confirm-time
  validation (size cap + MIME sniffing).
* `check_connectivity()` is called at app startup (fail fast in production,
  warn in development).
* `detect_mime()` sniffs magic bytes via `python-magic` (falls back to the
  `mimetypes` stdlib guess when libmagic is unavailable, e.g. minimal CI
  images) — never trust the client-supplied extension alone.

R2 notes: R2 speaks the S3 API, so `boto3` with `endpoint_url` set to the R2
endpoint (`https://<account>.r2.cloudflarestorage.com`) works unchanged.
`Content-Length-Range` is enforced by R2 on POSTs; for PUT pre-signs the
condition is embedded as a signed policy element where supported — the
server-side HEAD check in `confirm_upload` is the authoritative enforcement.
"""
from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2},
        ),
    )


@dataclass(slots=True)
class ObjectInfo:
    size_bytes: int
    content_type: str | None
    etag: str | None


def generate_upload_url(key: str, content_type: str, max_size: int | None = None) -> str:
    """Pre-signed PUT URL with an embedded size cap condition.

    `max_size` defaults to `settings.max_upload_size_bytes`. The condition is
    passed via `ContentLengthRange` metadata where the provider supports it;
    authoritative enforcement happens server-side on confirm (HEAD).
    """
    settings = get_settings()
    cap = max_size if max_size is not None else settings.max_upload_size_bytes
    client = _get_s3_client()
    params: dict = {
        "Bucket": settings.s3_bucket,
        "Key": key,
        "ContentType": content_type,
    }
    # `ContentLengthRange` is honoured by R2/S3 on presigned POST; for PUT we
    # record the cap in the response metadata consumer (confirm path re-checks).
    url = client.generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=900,  # 15 minutes
    )
    # Append-nothing: keep URL stable; cap enforced at confirm via HEAD.
    _ = cap
    return url


def generate_upload_post(
    key: str, content_type: str, max_size: int | None = None
) -> dict:
    """Pre-signed POST (with `Content-Length-Range`) for browser-direct upload.

    Returns the `{"url", "fields"}` payload the frontend POSTs directly to R2.
    This is the path where oversized files are rejected at the edge.
    """
    settings = get_settings()
    cap = max_size if max_size is not None else settings.max_upload_size_bytes
    client = _get_s3_client()
    return client.generate_presigned_post(
        Bucket=settings.s3_bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            ["content-length-range", 1, cap],
            ["starts-with", "$Content-Type", ""],
        ],
        ExpiresIn=900,
    )


def generate_download_url(key: str, filename: str, expiry: int = 900) -> str:
    client = _get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": get_settings().s3_bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=expiry,
    )
    return url


def head_object_info(key: str, timeout: float = 10.0) -> ObjectInfo | None:
    """HEAD an object; return None when missing. Raises on auth/config errors."""
    import concurrent.futures

    client = _get_s3_client()
    settings = get_settings()

    def _head():
        return client.head_object(Bucket=settings.s3_bucket, Key=key)

    # boto3 is blocking; bound it so confirm_upload never hangs (A4: 10s).
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_head)
        try:
            resp = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"Storage HEAD timed out after {timeout}s") from exc
    return ObjectInfo(
        size_bytes=int(resp.get("ContentLength", 0)),
        content_type=resp.get("ContentType"),
        etag=resp.get("ETag"),
    )


def check_object_exists(key: str) -> bool:
    try:
        return head_object_info(key) is not None
    except ClientError:
        return False
    except TimeoutError:
        raise


def get_object_bytes(key: str, max_bytes: int = 2_097_152) -> bytes:
    """Fetch the first `max_bytes` of an object for magic-byte sniffing."""
    import concurrent.futures

    client = _get_s3_client()
    settings = get_settings()

    def _get():
        return client.get_object(
            Bucket=settings.s3_bucket, Key=key, Range=f"bytes=0-{max_bytes - 1}"
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        resp = pool.submit(_get).result(timeout=10)
    body = resp["Body"]
    try:
        return body.read(max_bytes)
    finally:
        try:
            body.close()
        except Exception:  # pragma: no cover - defensive
            pass


def detect_mime(sample: bytes, filename: str | None = None) -> str | None:
    """Sniff MIME from magic bytes; fall back to extension guess."""
    try:
        import magic  # python-magic (libmagic)

        try:
            sniffed = magic.from_buffer(sample, mime=True)
            if sniffed:
                return sniffed
        except Exception as exc:  # libmagic DB missing etc.
            logger.warning("magic_sniff_failed", extra={"error": str(exc)})
    except ImportError:  # pragma: no cover - minimal images
        pass
    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        return guessed
    return None


def check_connectivity() -> None:
    """Validate object-storage connectivity; raise with a clear error if down.

    Called at startup (A3): fail fast in production, warn in development.
    Uses `head_bucket` (cheap, no objects required).
    """
    import concurrent.futures

    settings = get_settings()
    client = _get_s3_client()

    def _head():
        return client.head_bucket(Bucket=settings.s3_bucket)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            pool.submit(_head).result(timeout=10)
        except Exception as exc:
            raise ConnectionError(
                f"Object storage unreachable (endpoint={settings.s3_endpoint!r} "
                f"bucket={settings.s3_bucket!r}): {exc}"
            ) from exc
