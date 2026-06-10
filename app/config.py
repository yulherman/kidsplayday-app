from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://playday:playday@localhost:5432/playday"
    database_use_ssl: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_postgres_scheme(cls, v: str) -> str:
        # Railway injects postgres:// or postgresql:// — asyncpg needs postgresql+asyncpg://
        v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    openai_api_key: str = ""
    openai_api_keys: str = ""  # comma-separated; overrides openai_api_key if set
    openai_model: str = "gpt-4.1"

    openweather_api_key: str = ""

    apple_client_id: str = ""  # iOS bundle ID (Sign in with Apple audience)

    revenuecat_webhook_secret: str = ""

    allowed_origins: str = "http://localhost:8081,http://localhost:19006"

    # Link used in shareable cards' QR code; user's ?ref=CODE is appended.
    share_landing_url: str = "https://playday.app"

    class Config:
        env_file = ".env"


settings = Settings()
