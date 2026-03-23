import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    ENV: str = "development"

    # ---------------------------------------------------------------------------
    # Sandbox — Docker-based isolated execution
    #
    # Allowed operations inside the sandbox container:
    #   - Read /usr (Python interpreter + stdlib, read-only)
    #   - Write /tmp (submission file only, noexec, 16 MB limit)
    #   - CPU: capped via nano_cpus (SANDBOX_CPU_QUOTA)
    #   - Memory: capped via mem_limit (SANDBOX_MEM_LIMIT)
    #
    # Blocked by policy:
    #   - All network I/O (network_disabled=True)
    #   - All Linux capabilities (cap_drop=ALL)
    #   - Privilege escalation (no-new-privileges)
    #   - Process spawning / shell execution (seccomp profile blocks fork/execve/clone)
    #   - Writes to any path except /tmp
    #   - Running as root (user=nobody)
    #
    # SANDBOX_SECCOMP_PROFILE: path to a JSON seccomp profile that denies
    #   fork, vfork, clone, execve, execveat, and other process-spawning syscalls.
    #   Set to "" to disable (development only — never disable in production).
    # ---------------------------------------------------------------------------
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_TIMEOUT_SECONDS: int = 5
    SANDBOX_MEM_LIMIT: str = "64m"
    SANDBOX_CPU_QUOTA: int = 500_000_000
    SANDBOX_SECCOMP_PROFILE: str = "/app/seccomp/sandbox-deny-spawn.json"
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
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # JWT revocation TTL — keep revoked JTIs in Redis until their natural expiry.
    # Set equal to ACCESS_TOKEN_EXPIRE_MINUTES so the blacklist entry auto-expires.
    JWT_REVOCATION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "change-me-in-production":
    raise RuntimeError("JWT_SECRET_KEY must be set in production environment. Check CI secrets and .env")
