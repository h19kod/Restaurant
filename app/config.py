import secrets as _secrets

from pydantic_settings import BaseSettings


def _generate_secret_key() -> str:
    """Generate a random secret key for development. Production MUST set SECRET_KEY env var."""
    import warnings

    warnings.warn(
        "SECRET_KEY not set — using a random ephemeral key. "
        "Tokens will be invalidated on restart. Set SECRET_KEY in your environment for production.",
        stacklevel=2,
    )
    return _secrets.token_urlsafe(64)


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/restaurant_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/restaurant_db"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    TAX_RATE: float = 0.15

    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — comma-separated list of allowed origins (default: localhost dev ports)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8501,http://localhost:3000"

    # Stripe — leave empty to disable billing (system still works, just no payments)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_BASIC: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "restaurant@example.com"

    class Config:
        env_file = ".env"


settings = Settings()

if not settings.SECRET_KEY:
    settings.SECRET_KEY = _generate_secret_key()
