import httpx
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from app.db.session import get_db
from app.db.models import User, AnonSession, CodeSubmission, MetacognitiveMetric, HintEvent
from redis.exceptions import RedisError
from app.core.auth import hash_password, verify_password, create_access_token, require_real_user, revoke_token, decode_token
from app.api.v1.deps.auth_guard import get_current_user_id
from app.core.config import settings
from app.core.email import send_verification_email
from app.core.redis_client import get_redis

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_COOKIE_NAME = "debugger_session"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days, matches ACCESS_TOKEN_EXPIRE_MINUTES


def _set_auth_cookie(response: Response, token: str) -> None:
    """Attach a secure httpOnly SameSite=Lax session cookie to the response."""
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.ENV != "development",
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path="/")


_OAUTH_STATE_TTL = 600   # 10 min
_CODE_TTL_SECONDS = 300  # 5 min one-time auth code
_PROVIDER_TIMEOUT = 10   # seconds for all upstream OAuth HTTP calls

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ---------------------------------------------------------------------------
# Redis helpers for OAuth state and one-time auth codes
# ---------------------------------------------------------------------------

async def _store_oauth_state(state: str, provider: str) -> None:
    try:
        r = get_redis()
        await r.set(f"oauth_state:{state}", provider, ex=_OAUTH_STATE_TTL)
    except RedisError as exc:
        import logging
        logging.getLogger(__name__).error("Redis unavailable storing OAuth state: %s", exc)
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")


# Sentinel values returned by _consume_oauth_state so callers can map
# each outcome to a distinct redirect error code.
_OAUTH_STATE_MISSING = "__missing__"   # key not found or already expired
_OAUTH_STATE_UNAVAILABLE = "__unavailable__"  # Redis connectivity failure


async def _consume_oauth_state(state: str) -> str:
    """Atomically get-and-delete the OAuth state.

    Returns:
      - The provider string (e.g. "github") on success.
      - _OAUTH_STATE_MISSING  when the key is absent or already expired.
      - _OAUTH_STATE_UNAVAILABLE  when Redis is unreachable.
    """
    try:
        r = get_redis()
        pipe = r.pipeline()
        await pipe.get(f"oauth_state:{state}")
        await pipe.delete(f"oauth_state:{state}")
        results = await pipe.execute()
        value = results[0]
        return value if value is not None else _OAUTH_STATE_MISSING
    except RedisError as exc:
        import logging
        logging.getLogger(__name__).error("Redis unavailable consuming OAuth state: %s", exc)
        return _OAUTH_STATE_UNAVAILABLE


async def _issue_auth_code(jwt: str, email: Optional[str] = None, avatar_url: Optional[str] = None) -> str:
    """Store a one-time code in Redis with TTL. Returns the code.

    Profile fields (email, avatar_url) are stored server-side so they never
    appear in redirect URLs or browser history.
    """
    try:
        r = get_redis()
        code = secrets.token_urlsafe(32)
        payload = json.dumps({"jwt": jwt, "email": email or "", "avatar_url": avatar_url or ""})
        await r.set(f"auth_code:{code}", payload, ex=_CODE_TTL_SECONDS)
        return code
    except RedisError as exc:
        import logging
        logging.getLogger(__name__).error("Redis unavailable issuing auth code: %s", exc)
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")


async def _consume_auth_code(code: str) -> Optional[dict]:
    """Atomically get-and-delete the auth code. Returns dict with jwt/email/avatar_url or None."""
    try:
        r = get_redis()
        pipe = r.pipeline()
        await pipe.get(f"auth_code:{code}")
        await pipe.delete(f"auth_code:{code}")
        results = await pipe.execute()
        raw = results[0]
    except RedisError as exc:
        import logging
        logging.getLogger(__name__).error("Redis unavailable consuming auth code: %s", exc)
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        # Legacy plain-JWT value — treat as jwt-only with no profile
        return {"jwt": raw, "email": "", "avatar_url": ""}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_anon: bool = False


class MessageResponse(BaseModel):
    detail: str


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password must be 72 bytes or fewer')
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class MergeRequest(BaseModel):
    anon_id: str


class CodeExchangeRequest(BaseModel):
    code: str


# ---------------------------------------------------------------------------
# Session identity — lightweight rehydration endpoint
# ---------------------------------------------------------------------------

class MeResponse(BaseModel):
    sub: str
    anon: bool
    email: Optional[str] = None
    avatar_url: Optional[str] = None


@router.get("/auth/me", response_model=MeResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    debugger_session: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Return identity fields decoded from the session cookie (or Bearer token).
    Used by the frontend on page load to rehydrate authenticated state without
    storing the JWT in localStorage.
    """
    # Resolve the raw token the same way get_current_user_id does
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
    elif debugger_session:
        token = debugger_session

    is_anon = True
    email: Optional[str] = None
    avatar: Optional[str] = None

    if token:
        try:
            payload = decode_token(token)
            is_anon = bool(payload.get("anon", False))
            if not is_anon:
                # Fetch display fields from DB for real users
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    email = user.email
                    avatar = user.avatar_url
        except Exception:
            pass

    return MeResponse(sub=user_id, anon=is_anon, email=email, avatar_url=avatar)


# ---------------------------------------------------------------------------
# Logout — server-side token revocation
# ---------------------------------------------------------------------------

@router.post("/auth/logout", status_code=204)
async def logout(response: Response, authorization: Optional[str] = Header(None), debugger_session: Optional[str] = Cookie(None)):
    """
    Revoke the presented JWT by storing its JTI in Redis until natural expiry.
    Also clears the httpOnly session cookie.
    Accepts the token from either the Authorization: Bearer header (preferred)
    or the debugger_session cookie (fallback for cookie-only browser flows).
    """
    _clear_auth_cookie(response)
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
    elif debugger_session:
        token = debugger_session
    if not token:
        return
    try:
        payload = decode_token(token)
        jti = payload.get("jti", "")
        if jti:
            await revoke_token(jti)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Anonymous session
# ---------------------------------------------------------------------------

@router.post("/auth/anon", response_model=AuthResponse, status_code=201)
@limiter.limit("20/minute")
async def create_anon_session(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    anon = AnonSession()
    db.add(anon)
    await db.commit()
    await db.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)
    _set_auth_cookie(response, token)
    return AuthResponse(access_token=token, is_anon=True)


# ---------------------------------------------------------------------------
# Email auth
# ---------------------------------------------------------------------------

@router.post("/auth/register", response_model=MessageResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, req: EmailRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email, User.provider == "email"))
    existing = result.scalar_one_or_none()
    if existing:
        if existing.email_verified:
            raise HTTPException(status_code=409, detail="Email already registered")
        token = secrets.token_urlsafe(64)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)
        try:
            await send_verification_email(req.email, token, settings.BACKEND_URL)
        except Exception:
            raise HTTPException(status_code=503, detail="Failed to send verification email. Please try again.")
        existing.verification_token = token
        existing.verification_token_expires_at = expiry
        existing.hashed_password = hash_password(req.password)
        await db.commit()
        return MessageResponse(detail="Verification email sent. Please check your inbox.")

    token = secrets.token_urlsafe(64)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)
    try:
        await send_verification_email(req.email, token, settings.BACKEND_URL)
    except Exception:
        raise HTTPException(status_code=503, detail="Failed to send verification email. Please try again.")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        provider="email",
        email_verified=False,
        verification_token=token,
        verification_token_expires_at=expiry,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    return MessageResponse(detail="Verification email sent. Please check your inbox.")


@router.get("/auth/verify-email")
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error")
    if not user.verification_token_expires_at or user.verification_token_expires_at < datetime.now(timezone.utc):
        user.verification_token = None
        user.verification_token_expires_at = None
        await db.commit()
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=expired")
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db.commit()
    jwt = create_access_token(str(user.id))
    # Profile stored server-side — no email/avatar in the redirect URL.
    auth_code = await _issue_auth_code(jwt, email=user.email)
    return RedirectResponse(f"{settings.FRONTEND_URL}?code={auth_code}&verified=1")


@router.post("/auth/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: EmailLoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email, User.provider == "email"))
    user = result.scalar_one_or_none()
    if user is None or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
    token = create_access_token(str(user.id))
    _set_auth_cookie(response, token)
    return AuthResponse(access_token=token, email=user.email, avatar_url=user.avatar_url)


@router.post("/auth/login-code", response_model=MessageResponse)
@limiter.limit("10/minute")
async def login_code(request: Request, req: EmailLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Cross-origin landing-page login: authenticates the user and returns a
    one-time code that the tool frontend can exchange for a JWT + profile.
    Avoids the sessionStorage cross-origin handoff which fails when landing
    and tool run on different origins.
    """
    result = await db.execute(select(User).where(User.email == req.email, User.provider == "email"))
    user = result.scalar_one_or_none()
    if user is None or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
    jwt = create_access_token(str(user.id))
    code = await _issue_auth_code(jwt, email=user.email, avatar_url=user.avatar_url)
    return MessageResponse(detail=code)


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

@router.get("/auth/github")
async def github_login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    state = secrets.token_urlsafe(32)
    try:
        await _store_oauth_state(state, "github")
    except HTTPException:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=auth_unavailable")
    url = (
        f"{GITHUB_AUTH_URL}?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&redirect_uri={settings.BACKEND_URL}/api/v1/auth/github/callback"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/auth/github/callback")
async def github_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    provider = await _consume_oauth_state(state)
    if provider == _OAUTH_STATE_UNAVAILABLE:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=auth_unavailable")
    if provider == _OAUTH_STATE_MISSING or provider != "github":
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=oauth_state_invalid")

    try:
        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            token_res = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/github/callback",
                },
            )
            if not token_res.is_success:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_token_failed")
            try:
                token_data = token_res.json()
            except Exception:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_token_failed")

            access_token = token_data.get("access_token")
            if not access_token:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_token_failed")

            headers = {"Authorization": f"Bearer {access_token}"}
            user_res = await client.get(GITHUB_USER_URL, headers=headers)
            if not user_res.is_success:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_api_error")
            try:
                gh_user = user_res.json()
            except Exception:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_api_error")

            if "id" not in gh_user:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_api_error")

            email = gh_user.get("email")
            if not email:
                email_res = await client.get(GITHUB_EMAIL_URL, headers=headers)
                if email_res.is_success:
                    try:
                        emails = email_res.json()
                        if isinstance(emails, list):
                            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                            email = primary["email"] if primary else None
                    except Exception:
                        pass
    except (httpx.TimeoutException, httpx.NetworkError):
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=github_timeout")

    if not email:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=no_email")

    provider_id = str(gh_user["id"])
    avatar_url = gh_user.get("avatar_url")
    username = gh_user.get("login")

    try:
        user = await _get_or_create_oauth_user(db, "github", provider_id, email, username, avatar_url)
    except HTTPException as exc:
        if exc.status_code == 409:
            return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=account_conflict")
        raise

    jwt = create_access_token(str(user.id))
    # Profile stored server-side — no email/avatar in the redirect URL.
    auth_code = await _issue_auth_code(jwt, email=email, avatar_url=avatar_url)
    return RedirectResponse(f"{settings.FRONTEND_URL}?code={auth_code}")


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@router.get("/auth/google")
async def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    state = secrets.token_urlsafe(32)
    try:
        await _store_oauth_state(state, "google")
    except HTTPException:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=auth_unavailable")
    params = (
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.BACKEND_URL}/api/v1/auth/google/callback"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&state={state}"
    )
    return RedirectResponse(GOOGLE_AUTH_URL + params)


@router.get("/auth/google/callback")
async def google_callback(code: str = Query(...), state: str = Query(...), db: AsyncSession = Depends(get_db)):
    provider = await _consume_oauth_state(state)
    if provider == _OAUTH_STATE_UNAVAILABLE:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=auth_unavailable")
    if provider == _OAUTH_STATE_MISSING or provider != "google":
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=oauth_state_invalid")

    try:
        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            token_res = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/google/callback",
                    "grant_type": "authorization_code",
                },
            )
            if not token_res.is_success:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_token_failed")
            try:
                token_data = token_res.json()
            except Exception:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_token_failed")

            access_token = token_data.get("access_token")
            if not access_token:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_token_failed")

            user_res = await client.get(
                GOOGLE_USER_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if not user_res.is_success:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_api_error")
            try:
                g_user = user_res.json()
            except Exception:
                return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_api_error")
    except (httpx.TimeoutException, httpx.NetworkError):
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_timeout")

    if "sub" not in g_user:
        return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=google_api_error")

    provider_id = g_user["sub"]
    email = g_user.get("email")
    username = g_user.get("name")
    avatar_url = g_user.get("picture")

    try:
        user = await _get_or_create_oauth_user(db, "google", provider_id, email, username, avatar_url)
    except HTTPException as exc:
        if exc.status_code == 409:
            return RedirectResponse(f"{settings.FRONTEND_URL}?verified=error&error=account_conflict")
        raise

    jwt = create_access_token(str(user.id))
    # Profile stored server-side — no email/avatar in the redirect URL.
    auth_code = await _issue_auth_code(jwt, email=email, avatar_url=avatar_url)
    return RedirectResponse(f"{settings.FRONTEND_URL}?code={auth_code}")


# ---------------------------------------------------------------------------
# OAuth code exchange
# ---------------------------------------------------------------------------

@router.post("/auth/exchange", response_model=AuthResponse)
async def exchange_code(req: CodeExchangeRequest, response: Response):
    """Consume a one-time auth code and return the JWT + profile. Code is deleted on first use."""
    data = await _consume_auth_code(req.code)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or expired auth code")
    _set_auth_cookie(response, data["jwt"])
    return AuthResponse(
        access_token=data["jwt"],
        email=data.get("email") or None,
        avatar_url=data.get("avatar_url") or None,
    )


# ---------------------------------------------------------------------------
# Session merge
# ---------------------------------------------------------------------------

@router.post("/auth/merge")
async def merge_anon_session(
    req: MergeRequest,
    user_id: str = Depends(require_real_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer all anon session data to the authenticated user's session.

    MetacognitiveMetric rows are merged by summing totals and recomputing
    accuracy rather than reassigning session_id, which would cause a unique
    constraint collision when the user already has a metric row.
    All writes are in one transaction; on failure the DB is rolled back and
    the caller receives merged=False so the frontend can retry.
    """
    from uuid import UUID as _UUID
    try:
        anon_uuid = str(_UUID(req.anon_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid anon_id")

    anon = await db.get(AnonSession, anon_uuid)
    if not anon or anon.merged_into is not None:
        return {"merged": False, "reason": "already merged or not found"}

    try:
        # Reassign submissions and hint events to the authenticated session.
        await db.execute(
            CodeSubmission.__table__.update()
            .where(CodeSubmission.session_id == anon_uuid)
            .values(session_id=user_id)
        )
        await db.execute(
            HintEvent.__table__.update()
            .where(HintEvent.session_id == anon_uuid)
            .values(session_id=user_id)
        )

        # Conflict-safe metric merge: sum anon totals into the user row.
        from sqlalchemy import select as _select
        anon_metric_res = await db.execute(
            _select(MetacognitiveMetric).where(MetacognitiveMetric.session_id == anon_uuid)
        )
        anon_metric = anon_metric_res.scalar_one_or_none()

        if anon_metric:
            user_metric_res = await db.execute(
                _select(MetacognitiveMetric).where(MetacognitiveMetric.session_id == user_id)
            )
            user_metric = user_metric_res.scalar_one_or_none()

            if user_metric:
                # Merge totals into the existing user row and recompute accuracy.
                user_metric.total_predictions += anon_metric.total_predictions
                user_metric.correct_predictions += anon_metric.correct_predictions
                user_metric.accuracy_score = (
                    user_metric.correct_predictions / user_metric.total_predictions
                    if user_metric.total_predictions > 0 else 0.0
                )
                await db.delete(anon_metric)
            else:
                # No user row yet — reassign the anon row directly.
                anon_metric.session_id = user_id

        anon.merged_into = user_id
        await db.commit()
    except Exception:
        await db.rollback()
        return {"merged": False, "reason": "merge failed, please retry"}

    return {"merged": True}


# ---------------------------------------------------------------------------
# Helper — safe OAuth user upsert (no cross-provider email merge)
# ---------------------------------------------------------------------------

async def _get_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_id: str,
    email: Optional[str],
    username: Optional[str],
    avatar_url: Optional[str],
) -> User:
    result = await db.execute(
        select(User).where(User.provider == provider, User.provider_id == provider_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.avatar_url = avatar_url
        await db.commit()
        return user

    if email:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"An account with this email already exists. Please sign in with your original method ({existing.provider})."
            )

    user = User(
        email=email,
        username=username,
        provider=provider,
        provider_id=provider_id,
        avatar_url=avatar_url,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Race: another request inserted the same provider+provider_id concurrently.
        result = await db.execute(
            select(User).where(User.provider == provider, User.provider_id == provider_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.avatar_url = avatar_url
            await db.commit()
            return user
        # email uniqueness collision (race on email check above)
        raise HTTPException(status_code=409, detail="Account already exists. Please sign in with your original method.")
    await db.refresh(user)
    return user
