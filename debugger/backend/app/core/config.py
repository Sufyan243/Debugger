import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    ENV: str = "development"
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 3
    SANDBOX_MEM_LIMIT: str = "64m"
    SANDBOX_CPU_QUOTA: int = 500_000_000
    MAX_CODE_LENGTH: int = 10000
    FRONTEND_URL: str = "http://localhost:5173"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

if settings.ENV == "production" and settings.JWT_SECRET_KEY == "change-me-in-production":
    raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret in production")
