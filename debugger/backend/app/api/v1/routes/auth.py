import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.session import get_db
from app.db.models import User, AnonSession, CodeSubmission, MetacognitiveMetric, HintEvent
from app.core.auth import hash_password, verify_password, create_access_token, require_real_user
from app.core.config import settings

router = APIRouter()

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_anon: bool = False


class EmailAuthRequest(BaseModel):
    email: str
    password: str


class MergeRequest(BaseModel):
    anon_id: str


# --- Anonymous session ---

@router.post("/auth/anon", response_model=AuthResponse, status_code=201)
async def create_anon_session(db: AsyncSession = Depends(get_db)):
    anon = AnonSession()
    db.add(anon)
    await db.commit()
    await db.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)
    return AuthResponse(access_token=token, is_anon=True)


# --- Email auth ---

@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(req: EmailAuthRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        provider="email"
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, email=user.email)


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: EmailAuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email, User.provider == "email"))
    user = result.scalar_one_or_none()
    if user is None or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, email=user.email, avatar_url=user.avatar_url)


# --- GitHub OAuth ---

@router.get("/auth/github")
async def github_login():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    url = (
        f"{GITHUB_AUTH_URL}?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&redirect_uri={settings.FRONTEND_URL}/auth/github/callback"
    )
    return RedirectResponse(url)


@router.get("/auth/github/callback")
async def github_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.FRONTEND_URL}/auth/github/callback",
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed")

        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = await client.get(GITHUB_USER_URL, headers=headers)
        gh_user = user_res.json()

        email = gh_user.get("email")
        if not email:
            email_res = await client.get(GITHUB_EMAIL_URL, headers=headers)
            emails = email_res.json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else None

    provider_id = str(gh_user["id"])
    avatar_url = gh_user.get("avatar_url")
    username = gh_user.get("login")

    user = await _get_or_create_oauth_user(db, "github", provider_id, email, username, avatar_url)
    jwt = create_access_token(str(user.id))
    return RedirectResponse(f"{settings.FRONTEND_URL}?token={jwt}&email={email or ''}&avatar={avatar_url or ''}")


# --- Google OAuth ---

@router.get("/auth/google")
async def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    params = (
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.FRONTEND_URL}/auth/google/callback"
        f"&response_type=code"
        f"&scope=openid email profile"
    )
    return RedirectResponse(GOOGLE_AUTH_URL + params)


@router.get("/auth/google/callback")
async def google_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.FRONTEND_URL}/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google OAuth failed")

        user_res = await client.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        g_user = user_res.json()

    provider_id = g_user["sub"]
    email = g_user.get("email")
    username = g_user.get("name")
    avatar_url = g_user.get("picture")

    user = await _get_or_create_oauth_user(db, "google", provider_id, email, username, avatar_url)
    jwt = create_access_token(str(user.id))
    return RedirectResponse(f"{settings.FRONTEND_URL}?token={jwt}&email={email or ''}&avatar={avatar_url or ''}")


# --- Session merge ---

@router.post("/auth/merge")
async def merge_anon_session(
    req: MergeRequest,
    user_id: str = Depends(require_real_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer all anon session data to the authenticated user's session."""
    try:
        anon_uuid = req.anon_id
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid anon_id")

    anon = await db.get(AnonSession, anon_uuid)
    if not anon or anon.merged_into is not None:
        return {"merged": False, "reason": "already merged or not found"}

    # Reassign code submissions from anon session to user's session
    await db.execute(
        CodeSubmission.__table__.update()
        .where(CodeSubmission.session_id == anon_uuid)
        .values(session_id=user_id)
    )
    await db.execute(
        MetacognitiveMetric.__table__.update()
        .where(MetacognitiveMetric.session_id == anon_uuid)
        .values(session_id=user_id)
    )
    await db.execute(
        HintEvent.__table__.update()
        .where(HintEvent.session_id == anon_uuid)
        .values(session_id=user_id)
    )

    anon.merged_into = user_id
    await db.commit()
    return {"merged": True}


# --- Helper ---

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

    # Check if email already exists under different provider
    if email:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            existing.provider_id = provider_id
            existing.avatar_url = avatar_url
            await db.commit()
            return existing

    user = User(
        email=email,
        username=username,
        provider=provider,
        provider_id=provider_id,
        avatar_url=avatar_url,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
