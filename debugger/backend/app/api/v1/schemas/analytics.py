from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class ConceptStatItem(BaseModel):
    concept: str
    error_count: int
    attempts: int
    success_streak: int


class ConceptStatsResponse(BaseModel):
    concepts: List[ConceptStatItem]


class WeaknessProfileResponse(BaseModel):
    weak_concepts: List[ConceptStatItem]


class SessionSummaryResponse(BaseModel):
    submissions_count: int
    errors_count: int
    concepts_learned: int
    hints_used: int
    prediction_accuracy: float


class MetacognitiveResponse(BaseModel):
    session_id: UUID
    accuracy_score: float
    total_predictions: int
    correct_predictions: int
