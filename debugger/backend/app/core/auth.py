import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Header, Cookie
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.exceptions import RedisError
from app.core.config import settings

logger = logging.getLogger(__name__)

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, is_anon: bool = False) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    return jwt.encode(
        {"sub": user_id, "exp": expire, "anon": is_anon, "jti": jti},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """Returns payload dict with sub, anon, and jti, or raises JWTError."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("sub") is None:
        raise JWTError("Missing sub")
    if payload.get("jti") is None:
        raise JWTError("Missing jti")
    return payload


async def is_token_revoked(jti: str) -> bool:
    """Returns True if the JTI has been added to the Redis revocation set.
    Raises RedisError on connectivity failure — callers must handle it.
    """
    from app.core.redis_client import get_redis
    r = get_redis()
    return bool(await r.get(f"revoked_jti:{jti}"))


async def revoke_token(jti: str) -> None:
    """Persist the JTI in Redis until it would have naturally expired.
    Logs and swallows RedisError so logout always returns 204.
    """
    from app.core.redis_client import get_redis
    r = get_redis()
    try:
        await r.set(f"revoked_jti:{jti}", "1", ex=settings.JWT_REVOCATION_TTL_SECONDS)
    except RedisError as exc:
        logger.error("Redis unavailable during token revocation (jti=%s): %s", jti, exc)


async def require_real_user(
    authorization: Optional[str] = Header(None),
    debugger_session: Optional[str] = Cookie(None),
) -> str:
    """Requires a non-anonymous, non-revoked JWT. Raises 401/503 otherwise.

    Accepts the token from either:
      1. Authorization: Bearer <token>  (API clients)
      2. httpOnly cookie 'debugger_session'  (browser sessions)
    This mirrors get_current_user_id so cookie-based auth works on /auth/merge.
    """
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif debugger_session:
        token = debugger_session

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("anon"):
        raise HTTPException(status_code=401, detail="Login required")
    jti = payload.get("jti", "")
    if jti:
        try:
            if await is_token_revoked(jti):
                raise HTTPException(status_code=401, detail="Token has been revoked")
        except HTTPException:
            raise
        except RedisError as exc:
            logger.error("Redis unavailable during revocation check (require_real_user, jti=%s): %s", jti, exc)
            raise HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")
    return payload["sub"]
