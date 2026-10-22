from pydantic import BaseModel, Field


class GroundednessJudgment(BaseModel):
    grounded: bool
    score: float = Field(
        ge=0.0,
        le=1.0,
    )
    unsupported_claims: list[str]
    reasoning: str


class AnswerRecallJudgment(BaseModel):
    matched_fact_indices: list[int]
    reasoning: str


class AnswerRecallResult(BaseModel):
    recall: float = Field(
        ge=0.0,
        le=1.0,
    )
    matched_fact_indices: list[int]
    missed_fact_indices: list[int]
    reasoning: str
