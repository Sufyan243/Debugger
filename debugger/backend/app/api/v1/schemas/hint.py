from pydantic import BaseModel, validator
from uuid import UUID


class HintRequest(BaseModel):
    submission_id: UUID
    tier: int
    session_id: UUID
    
    @validator("tier")
    def validate_tier(cls, v: int) -> int:
        if v not in [1, 2, 3]:
            raise ValueError("Tier must be 1, 2, or 3")
        return v


class HintResponse(BaseModel):
    tier: int
    tier_name: str
    hint_text: str
    concept_category: str
