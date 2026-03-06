from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 3
    SANDBOX_MEM_LIMIT: str = "64m"
    SANDBOX_CPU_QUOTA: int = 500_000_000
    MAX_CODE_LENGTH: int = 10000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
