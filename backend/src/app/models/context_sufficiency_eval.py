from pydantic import BaseModel, Field


class ContextSufficiencyEvalCase(BaseModel):
    id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_sufficient: bool


class ContextSufficiencyEvidence(BaseModel):
    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class ContextSufficiencyJudgeOutput(BaseModel):
    sufficient: bool
    evidence: list[ContextSufficiencyEvidence]
    missing_information: list[str]
    reason: str = Field(min_length=1)


class ContextSufficiencyEvalResult(BaseModel):
    sufficient: bool
    evidence_chunk_ids: list[str]
    missing_information: list[str]
    reason: str
