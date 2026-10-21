from datetime import date, datetime

from pydantic import BaseModel

from app.models.company import CompanyDetail
from app.models.edinet import EdinetNarrativeSummary
from app.models.financial import FinancialSummary


class AnnualReportInfo(BaseModel):
    doc_id: str
    edinet_code: str
    sec_code: str | None = None

    period_start: date | None = None
    period_end: date | None = None

    submitted_at: datetime | None = None
    description: str | None = None


class CompanyResearchResult(BaseModel):
    company: CompanyDetail
    edinet_code: str
    annual_report: AnnualReportInfo
    financials: FinancialSummary
    narratives: EdinetNarrativeSummary
