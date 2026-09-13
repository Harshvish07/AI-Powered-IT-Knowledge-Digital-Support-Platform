from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]

# Settings that are safe to ship as convenient defaults for local development
# but that a production deployment must never actually run with. Checked by
# assert_production_safe() below, called once at app startup (app/main.py) —
# this makes an insecure production deploy fail loudly at boot instead of
# silently serving traffic with a known-public secret key.
_DEV_ONLY_JWT_SECRET = "dev-insecure-secret-change-me-before-deploying-anywhere"


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env.

    There is deliberately one Settings class, not one per environment
    (development/test/production) — every field has a safe, local-only
    default, and `ENVIRONMENT` plus `assert_production_safe()` are what
    actually separates the environments in practice: set the handful of
    environment variables documented in docs/deployment.md differently per
    environment, rather than maintaining parallel config classes.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI-Powered IT Knowledge & Digital Support Platform API"
    environment: Environment = "development"
    # False by default even in development: FastAPI's debug mode echoes full
    # tracebacks in 500 responses, which is useful locally but must never be
    # the default a fresh checkout runs with. Flip it on explicitly in a local
    # .env only when actively debugging an unhandled exception.
    debug: bool = False
    # Root log verbosity (standard Python logging level names). See
    # app/core/logging_config.py — log *format* (plain text vs JSON) is
    # decided separately, from `environment`.
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/itsupport"
    # SQLAlchemy connection pool sizing. Defaults are SQLAlchemy's own
    # defaults made explicit (and therefore tunable via env var) rather than
    # changed — this is a single-instance MVP, not a high-concurrency
    # service, so there's no evidence yet that the defaults are wrong. See
    # docs/deployment.md "Performance considerations".
    db_pool_size: int = 5
    db_max_overflow: int = 10
    # Recycle connections periodically so a managed Postgres provider that
    # silently drops idle connections (common on hosted free/small tiers)
    # can't accumulate stale connections in the pool.
    db_pool_recycle_seconds: int = 1800

    cors_origins: list[str] = ["http://localhost:3000"]

    # ---- Auth ----
    # Dev-only default; every deployment must override this with a strong random
    # value (e.g. `openssl rand -hex 32`). Never reuse this default in production.
    jwt_secret_key: str = _DEV_ONLY_JWT_SECRET
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

    # ---- RAG / AI assistant ----
    chat_model: str = "gemini-3.6-flash"
    chat_max_output_tokens: int = 1024
    # How many chunks to retrieve from pgvector before similarity filtering.
    rag_top_k: int = 5
    # Minimum cosine similarity (1 - cosine_distance) for a chunk to be used as
    # grounding evidence. Empirically measured against the seeded demo
    # knowledge base (gemini-embedding-001): genuinely relevant top hits
    # scored ~0.63-0.71, while clearly off-topic questions topped out around
    # ~0.51-0.52 — 0.55 sits cleanly between the two. Retune if real usage
    # shows too many/few chunks passing.
    rag_similarity_threshold: float = 0.55


@lru_cache
def get_settings() -> Settings:
    return Settings()


def assert_production_safe(settings: Settings) -> None:
    """Fails fast at startup if ENVIRONMENT=production is combined with a
    setting that is only ever safe for local development. This is the
    practical difference between "development" and "production" in this
    codebase — see the Settings docstring for why that's a deliberate choice
    over separate config classes. Raises RuntimeError (never silently warns)
    because an insecure production boot is a deploy-blocking bug, not a
    warning someone can reasonably ignore.
    """
    if settings.environment != "production":
        return

    problems: list[str] = []
    if settings.jwt_secret_key == _DEV_ONLY_JWT_SECRET:
        problems.append(
            "JWT_SECRET_KEY is still the development default — generate a real "
            "secret (e.g. `openssl rand -hex 32`) and set it in the environment."
        )
    if settings.debug:
        problems.append("DEBUG=true in production would echo tracebacks to clients.")
    if not settings.cookie_secure:
        problems.append(
            "COOKIE_SECURE=false in production would send the refresh-token cookie "
            "over plain HTTP. Set COOKIE_SECURE=true (requires serving over HTTPS)."
        )
    if any("localhost" in origin or "127.0.0.1" in origin for origin in settings.cors_origins):
        problems.append(
            "CORS_ORIGINS still includes a localhost origin — set it to your real "
            "frontend origin(s) only."
        )
    if not settings.gemini_api_key:
        problems.append(
            "GEMINI_API_KEY is not set — the knowledge base and AI assistant would "
            "be unusable (uploads would fail at the embedding step)."
        )

    if problems:
        raise RuntimeError(
            "Refusing to start with ENVIRONMENT=production and unsafe configuration:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )
