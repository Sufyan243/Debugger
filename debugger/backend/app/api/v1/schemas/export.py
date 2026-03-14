from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class SubmissionExportItem(BaseModel):
    submission_id: UUID
    timestamp: str
    code_text: str
    prediction: Optional[str]


class ErrorExportItem(BaseModel):
    submission_id: UUID
    exception_type: str
    concept_category: str
    cognitive_skill: Optional[str]


class ReflectionExportItem(BaseModel):
    submission_id: UUID
    response_text: str
    hint_unlocked: bool
    created_at: str


class PredictionExportItem(BaseModel):
    submission_id: UUID
    timestamp: str
    prediction: Optional[str]


class HintEventExportItem(BaseModel):
    submission_id: UUID
    hint_text: str
    affected_line: Optional[int]
    created_at: str


class SessionExportResponse(BaseModel):
    session_id: UUID
    submissions: List[SubmissionExportItem]
    errors: List[ErrorExportItem]
    reflections: List[ReflectionExportItem]
    predictions: List[PredictionExportItem]
    hints: List[HintEventExportItem]
