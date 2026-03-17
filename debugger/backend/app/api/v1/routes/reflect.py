from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.v1.schemas.reflect import ReflectRequest, ReflectResponse
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, ReflectionResponse

router = APIRouter()


@router.post("/reflect", response_model=ReflectResponse)
async def reflect_handler(
    request: ReflectRequest,
    db: AsyncSession = Depends(get_db),
    caller_id: str = Depends(get_current_user_id),
) -> ReflectResponse:
    # Verify the authenticated caller owns the session in the request body
    require_session_owner(request.session_id, caller_id)

    # Look up CodeSubmission and validate ownership
    stmt = select(CodeSubmission).where(
        CodeSubmission.id == request.submission_id,
        CodeSubmission.session_id == request.session_id
    )
    result = await db.execute(stmt)
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found or access denied")

    # Look up ExecutionResult and ErrorRecord
    stmt = select(ErrorRecord).join(ExecutionResult).where(
        ExecutionResult.submission_id == request.submission_id
    ).order_by(ExecutionResult.id.desc())
    result = await db.execute(stmt)
    error_record = result.scalars().first()
    if not error_record:
        raise HTTPException(status_code=404, detail="No error record found for this submission")

    # Create ReflectionResponse
    reflection = ReflectionResponse(
        submission_id=request.submission_id,
        response_text=request.response_text,
        hint_unlocked=True
    )
    db.add(reflection)
    await db.commit()
    await db.refresh(reflection)

    return ReflectResponse(
        accepted=True,
        hint_unlocked=True,
        reflection_id=reflection.id
    )
