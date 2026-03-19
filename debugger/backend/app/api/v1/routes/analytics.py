from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import MetacognitiveMetric
from app.intelligence.analytics_service import get_concept_stats, get_weakness_profile, get_session_summary
from app.api.v1.schemas.analytics import (
    ConceptStatItem,
    ConceptStatsResponse,
    WeaknessProfileResponse,
    SessionSummaryResponse,
    MetacognitiveResponse,
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
