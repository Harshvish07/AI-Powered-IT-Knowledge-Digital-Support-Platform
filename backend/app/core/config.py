from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI-Powered IT Knowledge & Digital Support Platform API"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/itsupport"

    cors_origins: list[str] = ["http://localhost:3000"]

    # ---- Auth ----
    # Dev-only default; every deployment must override this with a strong random
    # value (e.g. `openssl rand -hex 32`). Never reuse this default in production.
    jwt_secret_key: str = "dev-insecure-secret-change-me-before-deploying-anywhere"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "refresh_token"
    # Set to true once the app is served over HTTPS.
    cookie_secure: bool = False

    # ---- Dev-only admin seed (see app/scripts/seed_admin.py) ----
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    seed_admin_full_name: str = "Admin"

    # ---- Knowledge base / document ingestion ----
    max_upload_size_mb: int = 20
    # Relative to the backend working directory (the repo's backend/ folder in dev,
    # /app in the container) — kept out of the Python package tree on purpose.
    upload_storage_dir: str = "storage/uploads"
    chunk_size_tokens: int = 1000
    chunk_overlap_tokens: int = 150
    # Google Gemini embeddings (not OpenAI — this project uses Gemini for
    # embedding generation). Changing the model or dimensions after documents
    # exist requires a new migration for document_chunks.embedding and a full
    # reindex of existing documents.
    gemini_api_key: str | None = None
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()
