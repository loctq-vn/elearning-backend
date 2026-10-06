from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI E-Learning Platform"
    api_prefix: str = "/api"
    secret_key: str = "change-me-in-development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/elearning"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/elearning"
    aws_region: str = "ap-southeast-1"
    s3_bucket_name: str = "elearning-media"
    s3_public_base_url: str = ""
    openai_api_key: str = ""
    ai_primary_model: str = "gpt-4o-mini"
    ai_fallback_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    whisper_model_size: str = "small"
    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    emails_from_email: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
