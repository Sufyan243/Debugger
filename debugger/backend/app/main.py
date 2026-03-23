import logging
import json
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.redis_client import close_redis
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.execute import router as execute_router
from app.api.v1.routes.reflect import router as reflect_router
from app.api.v1.routes.hint import router as hint_router
from app.api.v1.routes.solution import router as solution_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.export import router as export_router
from app.api.v1.routes.session import router as session_router
from app.api.v1.routes.auth import router as auth_router


# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log)


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO if settings.ENV == "production" else logging.DEBUG)
    # Silence noisy third-party loggers
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import AsyncSessionLocal
    from app.db.seed import run_seed, run_hint_seed
    async with AsyncSessionLocal() as db:
        await run_seed(db)
        await run_hint_seed(db)
    yield
    await close_redis()


# Hide interactive docs in production — they expose the full API surface.
_docs_url = None if settings.ENV == "production" else "/docs"
_redoc_url = None if settings.ENV == "production" else "/redoc"

app = FastAPI(
    title="Cognitive Debugger API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# CSRF protection — Origin header validation for cookie-authenticated mutations
# ---------------------------------------------------------------------------

_CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Mutation endpoints that rely on the httpOnly cookie for auth
_CSRF_PROTECTED_PATHS = frozenset({
    "/api/v1/execute",
    "/api/v1/reflect",
    "/api/v1/hint",
    "/api/v1/solution-request",
    "/api/v1/auth/merge",
})


@app.middleware("http")
async def _csrf_origin_check(request: Request, call_next):
    """Reject cross-origin cookie-authenticated mutations.

    Allows requests that:
    - Use a safe HTTP method, OR
    - Are not on a CSRF-protected path, OR
    - Carry an Authorization: Bearer header (API clients — not cookie-based), OR
    - Have an Origin / Referer whose normalized scheme+host exactly matches an allowed origin.

    Rejects requests with a missing Origin AND Referer header.
    """
    if (
        request.method not in _CSRF_SAFE_METHODS
        and request.url.path in _CSRF_PROTECTED_PATHS
        and not request.headers.get("authorization", "").startswith("Bearer ")
    ):
        raw = request.headers.get("origin") or request.headers.get("referer")
        if not raw:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF check failed: missing Origin/Referer header"},
            )
        parsed = urlparse(raw)
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        if normalized not in settings.allowed_origins_list:
            return JSONResponse(
                status_code=403,
                content={"detail": f"CSRF check failed: origin {normalized!r} not allowed"},
            )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Request-ID + access log middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def _request_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(json.dumps({
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": elapsed_ms,
    }))
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(execute_router, prefix="/api/v1", tags=["execute"])
app.include_router(reflect_router, prefix="/api/v1", tags=["reflect"])
app.include_router(hint_router, prefix="/api/v1", tags=["hint"])
app.include_router(solution_router, prefix="/api/v1", tags=["solution"])
app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
app.include_router(export_router, prefix="/api/v1", tags=["export"])
app.include_router(session_router, prefix="/api/v1", tags=["session"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
