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

    # BYO API keys — Fernet key for encrypting user-supplied provider keys at rest.
    # Generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    KEYS_ENCRYPTION_KEY: str = ""

    # PJ-03 — Host-side Gemini key for the onboarding agent + vision pass.
    # Separate from the user's BYO pipeline key so new users can chat /
    # upload assets before they've entered their own pipeline key.
    # If empty, falls back to GEMINI_API_KEY for local dev convenience.
    AGENT_GEMINI_API_KEY: str = ""


settings = Settings()
