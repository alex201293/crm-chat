"""
Application configuration using pydantic-settings.
Loads from environment variables with .env file support.
Each settings class is grouped by domain for clarity.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "crm-chat"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = Field(min_length=32)
    APP_ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 4
    BACKEND_RELOAD: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "crm_chat"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = ""
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.DATABASE_USER,
                password=self.DATABASE_PASSWORD if self.DATABASE_PASSWORD else None,
                host=self.DATABASE_HOST,
                port=self.DATABASE_PORT,
                path=self.DATABASE_NAME,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=self.DATABASE_USER,
                password=self.DATABASE_PASSWORD,
                host=self.DATABASE_HOST,
                port=self.DATABASE_PORT,
                path=self.DATABASE_NAME,
            )
        )


class RedisSettings(BaseSettings):
    """Redis configuration for caching and pub/sub."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return str(
            RedisDsn.build(
                scheme="redis",
                password=self.REDIS_PASSWORD if self.REDIS_PASSWORD else None,
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                path=str(self.REDIS_DB),
            )
        )


class RabbitMQSettings(BaseSettings):
    """RabbitMQ configuration for async messaging."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )


class JWTSettings(BaseSettings):
    """JWT token configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    JWT_SECRET_KEY: str = Field(min_length=16)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7


class AISettings(BaseSettings):
    """AI provider configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Default provider and model
    DEFAULT_AI_PROVIDER: Literal["openai", "anthropic", "google", "mistral"] = "openai"
    DEFAULT_AI_MODEL: str = "gpt-4o"


class StorageSettings(BaseSettings):
    """File storage configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    STORAGE_DRIVER: Literal["local", "s3"] = "local"
    STORAGE_PATH: str = "./storage"
    AWS_S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"


class Settings:
    """
    Aggregated settings container.
    Access via get_settings() to benefit from caching.
    """

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.rabbitmq = RabbitMQSettings()
        self.jwt = JWTSettings()
        self.ai = AISettings()
        self.storage = StorageSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings factory.
    Call get_settings.cache_clear() if you need to reload (e.g., in tests).
    """
    return Settings()
