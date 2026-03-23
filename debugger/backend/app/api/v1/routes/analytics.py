from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.session import get_db
from app.db.models import MetacognitiveMetric, CodeSubmission, ExecutionResult, ErrorRecord
from app.intelligence.analytics_service import get_concept_stats, get_weakness_profile, get_session_summary, upsert_session_snapshot
from app.api.v1.schemas.analytics import (
    ConceptStatItem,
    ConceptStatsResponse,
    WeaknessProfileResponse,
    SessionSummaryResponse,
    MetacognitiveResponse,
    SessionHistoryItem,
    SessionHistoryResponse,
)
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner

router = APIRouter()


@router.get("/analytics/concepts", response_model=ConceptStatsResponse)
async def concepts_handler(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ConceptStatsResponse:
    require_session_owner(session_id, user_id)
    data = await get_concept_stats(session_id, db)
    return ConceptStatsResponse(concepts=[ConceptStatItem(**item) for item in data])


@router.get("/analytics/weakness", response_model=WeaknessProfileResponse)
async def weakness_handler(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> WeaknessProfileResponse:
    require_session_owner(session_id, user_id)
    data = await get_weakness_profile(session_id, db)
    return WeaknessProfileResponse(weak_concepts=[ConceptStatItem(**item) for item in data])


@router.get("/analytics/session-summary", response_model=SessionSummaryResponse)
async def session_summary_handler(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> SessionSummaryResponse:
    require_session_owner(session_id, user_id)
    summary = await get_session_summary(session_id, db)
    await upsert_session_snapshot(session_id, summary, db)
    return SessionSummaryResponse(**summary)


@router.get("/analytics/metacognitive", response_model=MetacognitiveResponse)
async def metacognitive_handler(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> MetacognitiveResponse:
    require_session_owner(session_id, user_id)
    stmt = select(MetacognitiveMetric).where(MetacognitiveMetric.session_id == session_id)
    result = await db.execute(stmt)
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="No metacognitive data found for this session")
    return MetacognitiveResponse(
        session_id=metric.session_id,
        accuracy_score=metric.accuracy_score,
        total_predictions=metric.total_predictions,
        correct_predictions=metric.correct_predictions,
    )


@router.get("/analytics/history", response_model=SessionHistoryResponse)
async def history_handler(
    session_id: UUID,
    q: str = Query(default="", description="Search term matched against code text and concept category"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> SessionHistoryResponse:
    require_session_owner(session_id, user_id)

    # Base query: submissions joined to their execution result and optional error record
    stmt = (
        select(
            CodeSubmission.id,
            CodeSubmission.timestamp,
            CodeSubmission.code_text,
            ExecutionResult.success_flag,
            ErrorRecord.exception_type,
            ErrorRecord.concept_category,
        )
        .join(ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id)
        .outerjoin(ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id)
        .where(CodeSubmission.session_id == session_id)
    )

    if q.strip():
        term = f"%{q.strip()}%"
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(
                CodeSubmission.code_text.ilike(term),
                ErrorRecord.concept_category.ilike(term),
            )
        )

    # Count total before pagination
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(desc(CodeSubmission.timestamp)).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).fetchall()

    items = [
        SessionHistoryItem(
            submission_id=row.id,
            timestamp=row.timestamp,
            code_snippet=row.code_text[:120],
            success=row.success_flag,
            exception_type=row.exception_type,
            concept_category=row.concept_category,
        )
        for row in rows
    ]
    return SessionHistoryResponse(items=items, total=total)
