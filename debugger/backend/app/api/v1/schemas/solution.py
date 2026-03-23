from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class SolutionRequestSchema(BaseModel):
    submission_id: UUID
    session_id: UUID


class SolutionResponse(BaseModel):
    request_count: int
    solution_revealed: bool
    solution_text: Optional[str] = None


class SolutionStateResponse(BaseModel):
    """Read-only state — returned by GET /solution-request/{id} without side effects."""
    request_count: int
    solution_revealed: bool
    solution_text: Optional[str] = None
