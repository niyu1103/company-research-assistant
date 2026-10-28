from pydantic import BaseModel, Field


class GroundednessContextChunk(BaseModel):
    chunk_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class GroundednessEvalInput(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    context_chunks: list[GroundednessContextChunk]


class GroundednessEvidence(BaseModel):
    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class GroundednessJudgeClaim(BaseModel):
    claim: str = Field(min_length=1)
    supported: bool
    evidence: list[GroundednessEvidence]
    reason: str = Field(min_length=1)


class GroundednessJudgeOutput(BaseModel):
    claims: list[GroundednessJudgeClaim] = Field(
        min_length=1,
    )


class GroundednessClaimEvaluation(BaseModel):
    claim: str = Field(min_length=1)
    supported: bool
    evidence_chunk_ids: list[str]
    reason: str = Field(min_length=1)


class GroundednessEvalResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    claims: list[GroundednessClaimEvaluation]
    unsupported_claims: list[str]
    reason: str
