from pydantic import BaseModel, Field


class CompanyDocumentQAInput(BaseModel):
    name: str = Field(min_length=1)
    question: str = Field(min_length=1)


class CompanyDocumentQASource(BaseModel):
    chunk_id: str
    section: str
    score: float


class CompanyDocumentQAResult(BaseModel):
    name: str
    question: str
    query_text: str
    answer: str
    evidence_chunk_ids: list[str]
    insufficient_context: bool
    sources: list[CompanyDocumentQASource]
