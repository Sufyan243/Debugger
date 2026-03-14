from fastapi import Depends, HTTPException, Header
from jose import JWTError
from app.core.auth import decode_token


def get_current_user_id(authorization: str = Header(...)) -> str:
    """Extracts user_id from 'Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
