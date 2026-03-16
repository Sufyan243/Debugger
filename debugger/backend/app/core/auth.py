from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

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
    return jwt.encode(
        {"sub": user_id, "exp": expire, "anon": is_anon},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_token(token: str) -> dict:
    """Returns payload dict with sub and anon flag, or raises JWTError."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("sub") is None:
        raise JWTError("Missing sub")
    return payload


def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extracts user_id from Bearer token. Returns None if no token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return payload["sub"]
    except JWTError:
        return None


def require_real_user(authorization: Optional[str] = Header(None)) -> str:
    """Requires a non-anonymous JWT. Raises 401 otherwise."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        if payload.get("anon"):
            raise HTTPException(status_code=401, detail="Login required")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
