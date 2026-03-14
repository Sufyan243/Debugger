import secrets
from uuid import UUID
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import SessionOwnership


async def verify_session_owner(
    session_id: UUID,
    x_session_token: str = Header(..., alias="X-Session-Token"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    stmt = select(SessionOwnership).where(SessionOwnership.session_id == session_id)
    result = await db.execute(stmt)
    ownership = result.scalar_one_or_none()
    if ownership is None or not secrets.compare_digest(ownership.owner_token, x_session_token):
        raise HTTPException(status_code=403, detail="Access denied: invalid session token")
    return session_id
