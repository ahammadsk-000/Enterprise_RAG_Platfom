"""Application configuration.

All settings are loaded from environment variables (12-factor) and validated at
startup so the process fails fast on misconfiguration. Settings are grouped into
nested models per concern (db, redis, qdrant, neo4j, auth, llm, storage, telemetry).

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings (async driver)."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "rag"
    password: str = "rag"
    db: str = "enterprise_rag"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dsn(self) -> str:
        """SQLAlchemy async DSN (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                path=self.db,
            )
        )


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dsn(self) -> str:
        return str(RedisDsn.build(scheme="redis", host=self.host, port=self.port, path=str(self.db)))


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")

    host: str = "localhost"
    port: int = 6333
    api_key: str | None = None
    collection_prefix: str = "rag"


class Neo4jSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEO4J_", extra="ignore")

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "neo4j_password"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_", extra="ignore")

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"  # RS256 in production
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14
    # OAuth / SSO (OIDC) — optional in local
    google_client_id: str | None = None
    google_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    # Frontend URL to redirect to after SSO callback (tokens appended in URL fragment).
    # If unset, the callback returns the token pair as JSON.
    sso_redirect_url: str | None = None


class LLMSettings(BaseSettings):
    """LLM + embedding provider config. Defaults to local Ollama."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    provider: Literal["ollama", "vllm", "openai"] = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    chat_model: str = "llama3.1:8b"
    embedding_provider: Literal["ollama", "sentence_transformers", "openai"] = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    request_timeout_s: int = 60


class StorageSettings(BaseSettings):
    """Object storage (S3-compatible / MinIO)."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")

    endpoint_url: str = "http://localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "rag-documents"
    region: str = "us-east-1"
    secure: bool = False


class TelemetrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OTEL_", extra="ignore")

    enabled: bool = True
    exporter_otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "enterprise-rag-api"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3001"


class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    project_name: str = "Enterprise RAG Platform"
    environment: Environment = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    # Comma-separated origins, e.g. "http://localhost:5173,https://app.example.com"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    # Per-client requests/minute (0 disables rate limiting).
    rate_limit_per_minute: int = 240
    # Demo/dev: run the ingestion pipeline inline (no Celery worker/broker needed).
    ingestion_inline: bool = False

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
