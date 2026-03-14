from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import User
from app.core.auth import hash_password, verify_password, create_access_token

router = APIRouter()


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    user = User(username=req.username, hashed_password=hash_password(req.password))
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, username=user.username)


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, username=user.username)
