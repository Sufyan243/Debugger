import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import SessionOwnership

router = APIRouter()


class SessionRegisterRequest(BaseModel):
    session_id: UUID


class SessionRegisterResponse(BaseModel):
    session_id: UUID
    owner_token: str


@router.post("/session/register", response_model=SessionRegisterResponse, status_code=201)
async def register_session(
    request: SessionRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionRegisterResponse:
    """
    Create-only session registration. Issues a server-generated owner_token for
    a new session_id. Returns 409 if the session_id is already registered —
    callers must use their stored token or call /session/recover with proof.
    """
    token = secrets.token_hex(32)
    db.add(SessionOwnership(session_id=request.session_id, owner_token=token))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Session already registered")

    return SessionRegisterResponse(session_id=request.session_id, owner_token=token)


@router.post("/session/recover", response_model=SessionRegisterResponse)
async def recover_session(
    request: SessionRegisterRequest,
    x_session_token: str = Header(..., alias="X-Session-Token"),
    db: AsyncSession = Depends(get_db),
) -> SessionRegisterResponse:
    """
    Authenticated token rotation. Requires the current valid X-Session-Token as
    proof of ownership. Issues a new token and invalidates the old one.
    Returns 401 if the session is not registered, 403 if the token is wrong.
    """
    stmt = select(SessionOwnership).where(SessionOwnership.session_id == request.session_id)
    result = await db.execute(stmt)
    ownership = result.scalar_one_or_none()

    if ownership is None:
        raise HTTPException(status_code=401, detail="Session not registered")

    if not secrets.compare_digest(ownership.owner_token, x_session_token):
        raise HTTPException(status_code=403, detail="Access denied: invalid session token")

    new_token = secrets.token_hex(32)
    ownership.owner_token = new_token
    await db.commit()

    return SessionRegisterResponse(session_id=request.session_id, owner_token=new_token)
