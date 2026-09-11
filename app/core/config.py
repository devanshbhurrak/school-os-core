"""Type-safe application configuration loaded from environment / .env.

All secrets live in the environment; nothing sensitive is ever committed.
Use `get_settings()` (cached) rather than constructing Settings directly.
"""
from __future__ import annotations

from functools import lru_cache

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

    # --- Rate limiting (Phase 1: in-process) ----------------------------
    login_rate_limit_per_minute: int = 5
    password_reset_rate_limit_per_hour: int = 3

    # --- Bootstrap ------------------------------------------------------
    bootstrap_org_code: str = "demo"
    bootstrap_org_name: str = "Demo Education Trust"
    bootstrap_school_code: str = "demo-hs"
    bootstrap_school_name: str = "Demo High School"
    bootstrap_admin_email: str = "admin@demo.test"

    @property
    def access_token_expire_seconds(self) -> int:
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        return self.refresh_token_expire_days * 24 * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
