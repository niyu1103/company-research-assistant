from pydantic import BaseModel, Field

from app.models.financial import FinancialTrend


class CompanyAnalysisDocumentContext(BaseModel):
    chunk_id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    content: str = Field(min_length=1)


class CompanyAnalysisQuestionInput(BaseModel):
    question: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    financial_trend: FinancialTrend
    documents: list[CompanyAnalysisDocumentContext]


class CompanyAnalysisQuestionAnswer(BaseModel):
    answer: str
    evidence_chunk_ids: list[str]
    insufficient_context: bool
