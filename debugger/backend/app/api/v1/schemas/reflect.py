from pydantic import BaseModel, Field
from uuid import UUID


class ReflectRequest(BaseModel):
    submission_id: UUID
    response_text: str = Field(min_length=10, max_length=2000)
    session_id: UUID


class ReflectResponse(BaseModel):
    accepted: bool
    hint_unlocked: bool
    reflection_id: UUID
