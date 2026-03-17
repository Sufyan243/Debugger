import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    ENV: str = "development"
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 5
    SANDBOX_MEM_LIMIT: str = "64m"
    SANDBOX_CPU_QUOTA: int = 500_000_000
    MAX_CODE_LENGTH: int = 10000
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30
    DEV_SKIP_EMAIL: bool = False

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

if settings.ENV == "production" and settings.JWT_SECRET_KEY == "change-me-in-production":
    raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret in production")
