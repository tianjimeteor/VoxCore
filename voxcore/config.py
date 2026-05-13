"""Application configuration.

All settings are sourced from environment variables (optionally via `.env`).
The loader refuses to yield an insecure default for security-critical fields.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known insecure placeholders that MUST NOT appear in a running deployment.
_INSECURE_JWT_PLACEHOLDERS = {
    "",
    "REPLACE_ME_OR_REFUSE_TO_START",
    "your-secret-key-change-in-production",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core auth ---
    jwt_secret_key: str = Field(
        default="REPLACE_ME_OR_REFUSE_TO_START",
        description="JWT signing key. Refuses to start if placeholder.",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Database ---
    database_url: str = "sqlite:///./voxcore.db"

    # --- Rate limiting ---
    login_rate_limit_max_attempts: int = 10
    login_rate_limit_window_seconds: int = 300
    login_lockout_duration_seconds: int = 900

    # --- Providers (empty = disabled) ---
    xunfei_app_id: str = ""
    xunfei_api_key: str = ""
    xunfei_api_secret: str = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    # --- Runtime ---
    voxcore_host: str = "0.0.0.0"  # noqa: S104 — binding all is intentional default
    voxcore_port: int = 8000
    voxcore_log_level: str = "INFO"

    # --- Security knobs ---
    min_password_length: int = 10
    ws_heartbeat_seconds: int = 60
    ws_max_message_bytes: int = 1_000_000  # 1 MB

    @field_validator("jwt_secret_key")
    @classmethod
    def _reject_insecure_jwt(cls, v: str) -> str:
        # Why: A default JWT secret silently deployed to production is the
        # single most common critical vulnerability in FastAPI apps.
        if v in _INSECURE_JWT_PLACEHOLDERS:
            raise ValueError(
                "JWT_SECRET_KEY is unset or uses a known placeholder. "
                "Generate a secure value: `python -m voxcore.cli gen-secret`"
            )
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters.")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Memoized settings accessor.

    Usage:
        from voxcore.config import get_settings
        settings = get_settings()
    """
    return Settings()
