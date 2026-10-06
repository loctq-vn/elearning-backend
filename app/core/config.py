from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI E-Learning Platform"
    api_prefix: str = "/api"
    secret_key: str = "change-me-in-development"
    access_token_expire_seconds: int = 900
    refresh_token_expire_days: int = 7
    app_timezone: str = "Asia/Ho_Chi_Minh"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/elearning"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/elearning"
    test_database_url: str = ""
    test_database_url_sync: str = ""

    aws_region: str = "ap-southeast-1"
    storage_endpoint_url: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    s3_bucket_name: str = "elearning-media"
    s3_public_base_url: str = ""
    cloudfront_domain: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    openai_api_key: str = ""
    gemini_api_key: str = ""
    ai_primary_model: str = "gpt-4o-mini"
    ai_fallback_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    whisper_model_size: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 5
    whisper_vad_filter: bool = True
    whisper_language: str = "vi"

    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    emails_from_email: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.app_env in {"staging", "production"} and self.secret_key == "change-me-in-development":
            raise ValueError("SECRET_KEY must be changed outside development")
        if self.embedding_dim <= 0:
            raise ValueError("EMBEDDING_DIM must be greater than zero")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
