import logging
from typing import Optional
from fastapi import HTTPException, Header, Cookie
from jose import JWTError
from redis.exceptions import RedisError
from app.core.auth import decode_token, is_token_revoked

logger = logging.getLogger(__name__)

_COOKIE_NAME = "debugger_session"


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    debugger_session: Optional[str] = Cookie(None),
) -> str:
    """
    Resolves the caller identity from either:
      1. Authorization: Bearer <token>  (API clients, existing flow)
      2. httpOnly cookie 'debugger_session'  (browser sessions, Comment 5)

    Returns 401 (not 422) when neither is present or both are malformed.
    Returns 503 if Redis is unreachable during revocation check.
    """
    token: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
    elif debugger_session:
        token = debugger_session

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    jti = payload.get("jti", "")
    if jti:
        try:
            if await is_token_revoked(jti):
                raise HTTPException(status_code=401, detail="Token has been revoked")
        except HTTPException:
            raise
        except RedisError as exc:
            logger.error("Redis unavailable during revocation check: %s", exc)
            raise HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")

    return str(payload["sub"])


def require_session_owner(session_id, user_id: str) -> None:
    """
    Raises 403 if the authenticated user does not own the requested session.

    The ownership invariant: after login the frontend always sets session_id to
    the JWT sub (User.id). For anonymous users the anon UUID is both the JWT sub
    and the session_id. In both cases ownership is proven by the JWT itself —
    no separate token is needed.

    Accepts session_id as UUID or str to avoid caller-side casting.
    """
    if str(session_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied to this session")
