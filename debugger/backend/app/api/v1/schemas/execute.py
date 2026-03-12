from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from app.core.config import settings


class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=settings.MAX_CODE_LENGTH)
    language: str
    session_id: UUID
    prediction: Optional[str] = Field(None, max_length=1000)
    
    @validator("language")
    def validate_language(cls, v: str) -> str:
        if v != "python":
            raise ValueError("Only python language is supported")
        return v


class ClassificationData(BaseModel):
    exception_type: str
    concept_category: str
    cognitive_skill: str


class ContextualHint(BaseModel):
    hint_text: str
    affected_line: Optional[int] = None
    explanation: str


class SolutionData(BaseModel):
    solution_code: str
    explanation: str
    changes_needed: list[str]


class ExecuteData(BaseModel):
    submission_id: UUID
    success: bool
    stdout: str
    stderr: str
    traceback: str
    execution_time: float
    classification: Optional[ClassificationData] = None
    reflection_question: Optional[str] = None
    contextual_hint: Optional[ContextualHint] = None
    solution: Optional[SolutionData] = None
    prediction_match: Optional[bool] = None
    metacognitive_accuracy: Optional[float] = None


class ExecuteResponse(BaseModel):
    status: str
    data: Optional[ExecuteData] = None
    message: str
    code: Optional[str] = None
