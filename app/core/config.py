"""
The office's operating manual: every environment-driven setting is checked
against this rulebook before the office is allowed to open. See
../../ANALOGY.md.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """The archive room's address — where the master ledger lives."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "vishesh.kapoor"
    password: str = "vishesh.kapoor"
    db: str = "retail-rag"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """The desk drawer where recently-used folders are kept close at hand."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 6379

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/0"


class MilvusSettings(BaseSettings):
    """The scent-sorted filing cabinet's address — where the dense vector
    index lives (T-M3.6). `collection` is overridden per-test the same way
    D-016 overrides `POSTGRES_DB`, so a test run's vectors never land in
    the collection a human is exploring."""

    model_config = SettingsConfigDict(env_prefix="MILVUS_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 19530
    collection: str = "chunk_embeddings"

    @property
    def uri(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseSettings):
    """
    The office's operating manual, assembled once at startup.

    Office workflow:
      1. Read every setting from the environment (or a local .env file for
         development), falling back to defaults only where a default is
         actually safe to ship.
      2. Validate each one against its declared type immediately — an
         invalid setting fails the office's opening checklist here, not
         partway through a visitor's request.
      3. Keep the archive room's (Postgres) and desk drawer's (Redis)
         settings as their own sub-manuals, so this top-level manual stays
         readable as more sections get added in later milestones.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)


@lru_cache
def get_settings() -> Settings:
    """Parses the operating manual once and hands out the same copy to every request."""
    return Settings()
