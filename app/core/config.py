"""Type-safe application configuration loaded from environment / .env.

All secrets live in the environment; nothing sensitive is ever committed.
Use `get_settings()` (cached) rather than constructing Settings directly.
"""
from __future__ import annotations

from functools import lru_cache

from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ----------------------------------------------------
    environment: str = "development"
    debug: bool = False
    app_name: str = "school-os-api"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Security -------------------------------------------------------
    secret_key: str = "change-me-generate-a-random-64-byte-value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15

    # --- Database -------------------------------------------------------
    database_url: str = "postgresql+asyncpg://school_os_app:school_os_app_dev@localhost:5432/school_os"
    migration_database_url: str = (
        "postgresql+asyncpg://school_os_migrator:school_os_migrator_dev@localhost:5432/school_os"
    )
    test_database_url: str | None = None
    sync_database_url: str | None = None
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # --- Logging --------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

    # --- S3 / Object Storage --------------------------------------------
    s3_endpoint: str | None = None
    s3_bucket: str = "school-os-documents"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # --- Rate limiting (Phase 3: Redis-backed, Upstash-compatible) --------
    login_rate_limit_per_minute: int = 5
    password_reset_rate_limit_per_hour: int = 3
    # Upstash Redis URL (rediss://... for TLS). Empty = in-memory fallback (dev/test).
    redis_url: str | None = None
    redis_pool_max_connections: int = 20
    redis_socket_timeout_seconds: float = 2.0
    rate_limit_enabled: bool = True

    # --- Documents / Uploads (Phase 3: R2-hardened) ------------------------
    max_upload_size_bytes: int = 52_428_800  # 50 MiB default
    allowed_mime_types: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "text/csv",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    # --- Timeouts (Phase 3) ------------------------------------------------
    bulk_import_timeout_seconds: float = 300.0
    document_confirm_timeout_seconds: float = 10.0

    # --- Outbox dispatcher (Phase 3) ---------------------------------------
    outbox_poll_interval_seconds: float = 5.0
    outbox_batch_size: int = 25
    outbox_max_attempts: int = 5

    # --- Bootstrap ------------------------------------------------------
    bootstrap_org_code: str = "demo"
    bootstrap_org_name: str = "Demo Education Trust"
    bootstrap_school_code: str = "demo-hs"
    bootstrap_school_name: str = "Demo High School"
    bootstrap_admin_email: str = "admin@demo.test"

    @model_validator(mode="after")
    def _validate_secret_key(self) -> Self:
        if self.environment != "development" and self.secret_key == "change-me-generate-a-random-64-byte-value":
            raise ValueError("SECRET_KEY must be changed from default in non-development environments")
        return self

    @property
    def access_token_expire_seconds(self) -> int:
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        return self.refresh_token_expire_days * 24 * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
