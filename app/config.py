# Ad-Ops-Autopilot — Application config (Pydantic Settings)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nerdy"
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
