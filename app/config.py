# Ad-Ops-Autopilot — Application config (Pydantic Settings)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nerdy"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth — legacy (kept for backward compat)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_EXPIRY_HOURS: int = 24

    # Auth — Clerk JWT validation (PG-01)
    CLERK_JWKS_URL: str = ""
    CLERK_ISSUER: str = ""
    DEV_MODE: bool = False


settings = Settings()
