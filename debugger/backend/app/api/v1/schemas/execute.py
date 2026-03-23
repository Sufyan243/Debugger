from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from app.core.config import settings


class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=settings.MAX_CODE_LENGTH)
    language: str
    session_id: UUID
    prediction: Optional[str] = Field(None, max_length=1000)

    @validator("code")
    def code_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code must not be empty or whitespace only")
        return v

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
    prediction_match: Optional[bool] = None
    metacognitive_accuracy: Optional[float] = None
    failed_attempts: Optional[int] = None


class ExecuteResponse(BaseModel):
    status: str
    data: Optional[ExecuteData] = None
    message: str
    code: Optional[str] = None
    # UNCHANGED_CODE is returned when the submitted code is identical to the
    # most recent submission for this session. The client must show a correction
    # prompt; no execution is performed and no submission row is written.
    # code == "UNCHANGED_CODE" when status == "unchanged".
