"""
Auditex -- application config.
Reads all settings from environment variables (loaded from .env in development).
Pydantic-settings validates types and raises on missing required values.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(default="placeholder")
    CLAUDE_MODEL: str = Field(default="claude-sonnet-4-6")

    # OpenAI
    OPENAI_API_KEY: str = Field(default="placeholder")
    GPT4O_MODEL: str = Field(default="gpt-4o")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://auditex:auditex_dev_pw@localhost:5432/auditex"
    )
    POSTGRES_USER: str = Field(default="auditex")
    POSTGRES_PASSWORD: str = Field(default="auditex_dev_pw")
    POSTGRES_DB: str = Field(default="auditex")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Vertex / FoxMQ
    FOXMQ_BROKER_URL: str = Field(default="mqtt://localhost:1883")
    VERTEX_NODE_URL: str = Field(default="http://localhost:8545")
    VERTEX_PRIVATE_KEY: str = Field(default="placeholder")

    # Security
    JWT_SECRET: str = Field(default="dev_secret_change_in_production")
    API_KEY_SALT: str = Field(default="dev_salt_change_in_production")

    # App
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    API_PORT: int = Field(default=8000)


# Singleton -- imported everywhere as `from app.config import settings`
settings = Settings()
