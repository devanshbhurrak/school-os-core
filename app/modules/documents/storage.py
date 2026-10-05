"""S3-compatible storage abstraction for document uploads/downloads."""
from __future__ import annotations

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import get_settings


def _get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(signature_version="s3v4"),
    )


def generate_upload_url(key: str, content_type: str, max_size: int = 10_485_760) -> str:
    client = _get_s3_client()
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": get_settings().s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=900,  # 15 minutes
    )
    return url


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


def check_object_exists(key: str) -> bool:
    client = _get_s3_client()
    try:
        client.head_object(Bucket=get_settings().s3_bucket, Key=key)
        return True
    except client.exceptions.ClientError:
        return False
