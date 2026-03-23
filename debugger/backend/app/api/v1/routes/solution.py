from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.v1.schemas.solution import SolutionRequestSchema, SolutionResponse, SolutionStateResponse
from app.db.session import get_db
from app.db.models import SolutionRequest, ErrorRecord, ExecutionResult, HintSequence, CodeSubmission, ReflectionResponse, HintEvent
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner
from uuid import UUID

router = APIRouter()


async def _fetch_solution_text(db: AsyncSession, concept_category: str) -> str | None:
    stmt = select(HintSequence).where(
        HintSequence.concept_category == concept_category,
        HintSequence.tier == 3
    )
    result = await db.execute(stmt)
    hint = result.scalars().first()
    return hint.hint_text if hint else None


async def _has_tier3_unlocked(db: AsyncSession, submission_id: UUID) -> bool:
    """Returns True when a tier-3 HintEvent has been explicitly persisted for this submission."""
    stmt = select(HintEvent).where(
        HintEvent.submission_id == submission_id,
        HintEvent.tier == 3,
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None


@router.get("/solution-request/{submission_id}", response_model=SolutionStateResponse)
async def get_solution_state(
    submission_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    caller_id: str = Depends(get_current_user_id),
) -> SolutionStateResponse:
    """Read-only: returns current solution state without incrementing request_count."""
    require_session_owner(session_id, caller_id)

    stmt = select(CodeSubmission).where(
        CodeSubmission.id == submission_id,
        CodeSubmission.session_id == session_id
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Submission not found or access denied")

    stmt = select(SolutionRequest).where(SolutionRequest.submission_id == submission_id)
    result = await db.execute(stmt)
    solution_req = result.scalars().first()

    if solution_req is None:
        return SolutionStateResponse(request_count=0, solution_revealed=False, solution_text=None)

    solution_text = None
    if solution_req.solution_revealed:
        stmt = select(ErrorRecord).join(ExecutionResult).where(
            ExecutionResult.submission_id == submission_id
        ).order_by(ExecutionResult.id.desc())
        result = await db.execute(stmt)
        error_record = result.scalars().first()
        if error_record:
            solution_text = await _fetch_solution_text(db, error_record.concept_category)

    return SolutionStateResponse(
        request_count=solution_req.request_count,
        solution_revealed=solution_req.solution_revealed,
        solution_text=solution_text,
    )


@router.post("/solution-request", response_model=SolutionResponse)
async def solution_request_handler(
    request: SolutionRequestSchema,
    db: AsyncSession = Depends(get_db),
    caller_id: str = Depends(get_current_user_id),
) -> SolutionResponse:
    require_session_owner(request.session_id, caller_id)
    # Validate submission ownership
    stmt = select(CodeSubmission).where(
        CodeSubmission.id == request.submission_id,
        CodeSubmission.session_id == request.session_id
    )
    result = await db.execute(stmt)
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found or access denied")

    # Gate: reflection must exist before solution access is allowed.
    stmt = select(ReflectionResponse).where(
        ReflectionResponse.submission_id == request.submission_id
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(
            status_code=403,
            detail="Complete the reflection step before requesting the solution."
        )

    # Gate: tier-3 hint must have been unlocked before the solution is accessible.
    if not await _has_tier3_unlocked(db, request.submission_id):
        raise HTTPException(
            status_code=403,
            detail="Unlock all three hint tiers before requesting the solution."
        )

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
        solution_text = await _fetch_solution_text(db, error_record.concept_category)
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
        solution_text = await _fetch_solution_text(db, error_record.concept_category)

    return SolutionResponse(
        request_count=solution_req.request_count,
        solution_revealed=solution_req.solution_revealed,
        solution_text=solution_text
    )
