from contextlib import asynccontextmanager
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

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations must be run via the pre-start script (scripts/migrate.sh)
    # or an init container — NOT here, to avoid blocking the event loop.
    from app.db.session import AsyncSessionLocal
    from app.db.seed import run_seed, run_hint_seed
    async with AsyncSessionLocal() as db:
        await run_seed(db)
        await run_hint_seed(db)
    yield
    await close_redis()


app = FastAPI(title="Cognitive Debugger API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(execute_router, prefix="/api/v1", tags=["execute"])
app.include_router(reflect_router, prefix="/api/v1", tags=["reflect"])
app.include_router(hint_router, prefix="/api/v1", tags=["hint"])
app.include_router(solution_router, prefix="/api/v1", tags=["solution"])
app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
app.include_router(export_router, prefix="/api/v1", tags=["export"])
app.include_router(session_router, prefix="/api/v1", tags=["session"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
