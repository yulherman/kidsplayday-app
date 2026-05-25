from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://playday:playday@localhost:5432/playday"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"

    openweather_api_key: str = ""

    allowed_origins: str = "http://localhost:8081,http://localhost:19006"

    class Config:
        env_file = ".env"


settings = Settings()
