from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from app.core.config import settings


class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=settings.MAX_CODE_LENGTH)
    language: str
    session_id: UUID
    prediction: Optional[str] = Field(None, max_length=1000)
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v != "python":
            raise ValueError("Only python language is supported")
        return v


class ClassificationData(BaseModel):
    exception_type: str
    concept_category: str
    cognitive_skill: str


class HintData(BaseModel):
    tier: int
    tier_name: str
    hint_text: str
    unlocked: bool


class ExecuteData(BaseModel):
    submission_id: UUID
    success: bool
    stdout: str
    stderr: str
    traceback: str
    execution_time: float
    classification: Optional[ClassificationData] = None
    reflection_question: Optional[str] = None
    hints: Optional[list[HintData]] = None
    hint_auto_unlocked: bool = False


class ExecuteResponse(BaseModel):
    status: str
    data: Optional[ExecuteData] = None
    message: str
    code: Optional[str] = None
