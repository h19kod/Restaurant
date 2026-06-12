from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/restaurant_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/restaurant_db"
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    TAX_RATE: float = 0.15

    REDIS_URL: str = "redis://localhost:6379/0"

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
