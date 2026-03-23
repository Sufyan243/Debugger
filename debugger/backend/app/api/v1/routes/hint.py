from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.v1.schemas.hint import HintRequest, HintResponse
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, HintSequence, ReflectionResponse, HintEvent
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner

router = APIRouter()


@router.post("/hint", response_model=HintResponse)
async def hint_handler(
    request: HintRequest,
    db: AsyncSession = Depends(get_db),
    caller_id: str = Depends(get_current_user_id),
) -> HintResponse:
    require_session_owner(request.session_id, caller_id)

    stmt = select(CodeSubmission).where(
        CodeSubmission.id == request.submission_id,
        CodeSubmission.session_id == request.session_id
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Submission not found or access denied")

    # Gate: reflection must exist before any hint is served.
    stmt = select(ReflectionResponse).where(
        ReflectionResponse.submission_id == request.submission_id
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(
            status_code=403,
            detail="Complete the reflection step before requesting a hint."
        )

    # Gate: enforce tier progression using explicit tier history.
    # Find the highest tier already served for this submission.
    stmt = select(HintEvent).where(
        HintEvent.submission_id == request.submission_id,
        HintEvent.tier == request.tier,
    )
    result = await db.execute(stmt)
    already_served = result.scalars().first()

    if not already_served:
        # Determine the highest tier already unlocked for this submission.
        # Exclude legacy null-tier rows — they carry no progression information.
        stmt = select(HintEvent).where(
            HintEvent.submission_id == request.submission_id,
            HintEvent.tier.isnot(None),
        ).order_by(HintEvent.tier.desc())
        result = await db.execute(stmt)
        latest_event = result.scalars().first()
        highest_served = (latest_event.tier or 0) if latest_event else 0
        allowed_next = highest_served + 1

        if request.tier > allowed_next:
            raise HTTPException(
                status_code=403,
                detail=f"Hint tier {request.tier} is not yet unlocked. "
                       f"Complete tier {allowed_next} first."
            )

    # Look up ErrorRecord to get concept_category.
    stmt = select(ErrorRecord).join(ExecutionResult).where(
        ExecutionResult.submission_id == request.submission_id
    ).order_by(ExecutionResult.id.desc())
    result = await db.execute(stmt)
    error_record = result.scalars().first()
    if not error_record:
        raise HTTPException(status_code=404, detail="No error record found")

    # Query HintSequence for the requested tier.
    # Fallback: if the exact tier is missing, return the nearest lower tier.
    stmt = select(HintSequence).where(
        HintSequence.concept_category == error_record.concept_category,
        HintSequence.tier == request.tier
    )
    result = await db.execute(stmt)
    hint = result.scalars().first()

    if not hint:
        stmt = select(HintSequence).where(
            HintSequence.concept_category == error_record.concept_category,
            HintSequence.tier <= request.tier
        ).order_by(HintSequence.tier.desc())
        result = await db.execute(stmt)
        hint = result.scalars().first()

    if not hint:
        raise HTTPException(
            status_code=404,
            detail=f"No hints available for concept '{error_record.concept_category}'. "
                   "Please contact support."
        )

    # Persist the unlock event for this tier if not already recorded.
    if not already_served:
        db.add(HintEvent(
            submission_id=request.submission_id,
            session_id=request.session_id,
            hint_text=hint.hint_text,
            tier=hint.tier,
        ))
        await db.commit()

    return HintResponse(
        tier=hint.tier,
        tier_name=hint.tier_name,
        hint_text=hint.hint_text,
        concept_category=hint.concept_category
    )
