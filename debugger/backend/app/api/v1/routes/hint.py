from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.v1.schemas.hint import HintRequest, HintResponse
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, HintSequence

router = APIRouter()


@router.post("/hint", response_model=HintResponse)
async def hint_handler(request: HintRequest, db: AsyncSession = Depends(get_db)) -> HintResponse:
    # Validate submission ownership
    stmt = select(CodeSubmission).where(
        CodeSubmission.id == request.submission_id,
        CodeSubmission.session_id == request.session_id
    )
    result = await db.execute(stmt)
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found or access denied")
    
    # Look up ErrorRecord to get concept_category
    stmt = select(ErrorRecord).join(ExecutionResult).where(
        ExecutionResult.submission_id == request.submission_id
    ).order_by(ExecutionResult.id.desc())
    result = await db.execute(stmt)
    error_record = result.scalars().first()
    if not error_record:
        raise HTTPException(status_code=404, detail="No error record found")
    
    # Query HintSequence
    stmt = select(HintSequence).where(
        HintSequence.concept_category == error_record.concept_category,
        HintSequence.tier == request.tier
    )
    result = await db.execute(stmt)
    hint = result.scalars().first()
    if not hint:
        raise HTTPException(status_code=404, detail="Hint not found")
    
    return HintResponse(
        tier=hint.tier,
        tier_name=hint.tier_name,
        hint_text=hint.hint_text,
        concept_category=hint.concept_category
    )
