from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.v1.schemas.solution import SolutionRequestSchema, SolutionResponse
from app.db.session import get_db
from app.db.models import SolutionRequest, ErrorRecord, ExecutionResult, HintSequence, CodeSubmission

router = APIRouter()


@router.post("/solution-request", response_model=SolutionResponse)
async def solution_request_handler(request: SolutionRequestSchema, db: AsyncSession = Depends(get_db)) -> SolutionResponse:
    # Validate submission ownership
    stmt = select(CodeSubmission).where(
        CodeSubmission.id == request.submission_id,
        CodeSubmission.session_id == request.session_id
    )
    result = await db.execute(stmt)
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found or access denied")
    
    # Validate classified error exists
    stmt = select(ErrorRecord).join(ExecutionResult).where(
        ExecutionResult.submission_id == request.submission_id
    ).order_by(ExecutionResult.id.desc())
    result = await db.execute(stmt)
    error_record = result.scalars().first()
    if not error_record:
        raise HTTPException(status_code=404, detail="No classified error found for this submission")
    
    # Upsert SolutionRequest
    stmt = select(SolutionRequest).where(SolutionRequest.submission_id == request.submission_id)
    result = await db.execute(stmt)
    solution_req = result.scalars().first()
    
    # Short-circuit if already revealed
    if solution_req and solution_req.solution_revealed:
        # Fetch solution text
        stmt = select(HintSequence).where(
            HintSequence.concept_category == error_record.concept_category,
            HintSequence.tier == 3
        )
        result = await db.execute(stmt)
        hint = result.scalars().first()
        solution_text = hint.hint_text if hint else None
        
        return SolutionResponse(
            request_count=solution_req.request_count,
            solution_revealed=True,
            solution_text=solution_text
        )
    
    if solution_req:
        solution_req.request_count = min(solution_req.request_count + 1, 3)
        solution_req.last_requested_at = func.now()
    else:
        solution_req = SolutionRequest(
            submission_id=request.submission_id,
            request_count=1,
            last_requested_at=func.now()
        )
        db.add(solution_req)
    
    await db.commit()
    await db.refresh(solution_req)
    
    solution_text = None
    if solution_req.request_count >= 3:
        solution_req.solution_revealed = True
        await db.commit()
        
        # Fetch Tier 3 hint as solution proxy
        stmt = select(HintSequence).where(
            HintSequence.concept_category == error_record.concept_category,
            HintSequence.tier == 3
        )
        result = await db.execute(stmt)
        hint = result.scalars().first()
        if hint:
            solution_text = hint.hint_text
    
    return SolutionResponse(
        request_count=solution_req.request_count,
        solution_revealed=solution_req.solution_revealed,
        solution_text=solution_text
    )
