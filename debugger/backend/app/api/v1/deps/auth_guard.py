from fastapi import Depends, HTTPException, Header
from jose import JWTError
from app.core.auth import decode_token


def get_current_user_id(authorization: str = Header(...)) -> str:
    """Extracts and returns the subject identifier from 'Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
        return str(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_session_owner(session_id: str, user_id: str) -> None:
    """Raises 403 if the authenticated user does not own the requested session."""
    if str(session_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied to this session")
