from pydantic import BaseModel, Field


class RetrievalEvalCase(BaseModel):
    id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_chunk_ids: list[str] = Field(min_length=1)


class RetrievalEvalMetrics(BaseModel):
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float
