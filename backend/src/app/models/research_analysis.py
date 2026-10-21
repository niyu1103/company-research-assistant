from pydantic import BaseModel, Field

from app.models.financial import FinancialTrend
from app.models.research import CompanyResearchResult


class FinancialDerivedMetrics(BaseModel):
    operating_margin: float | None = None
    net_margin: float | None = None
    operating_cash_flow_margin: float | None = None


class FinancialDisplayValues(BaseModel):
    revenue: str | None = None
    operating_income: str | None = None
    profit_before_tax: str | None = None
    net_income: str | None = None
    total_assets: str | None = None
    operating_cash_flow: str | None = None


class BusinessAnalysis(BaseModel):
    summary: str
    main_products_and_services: list[str] = Field(default_factory=list)
    characteristics: list[str] = Field(default_factory=list)


class RiskAnalysis(BaseModel):
    category: str
    summary: str


class FinancialAnalysis(BaseModel):
    summary: str
    notable_points: list[str] = Field(default_factory=list)


class CompanyNarrativeAnalysis(BaseModel):
    business: BusinessAnalysis
    risks: list[RiskAnalysis] = Field(default_factory=list)


class CompanyAnalysis(BaseModel):
    business: BusinessAnalysis
    risks: list[RiskAnalysis] = Field(default_factory=list)
    financials: FinancialAnalysis


class CompanyAnalysisResearch(BaseModel):
    company_name: str
    business_overview: str | None = None
    business_risks: str | None = None


class CompanyAnalysisInput(BaseModel):
    research: CompanyAnalysisResearch


class CompanyResearchAnalysisResult(BaseModel):
    research: CompanyResearchResult
    derived_financials: FinancialDerivedMetrics
    display_financials: FinancialDisplayValues
    financial_trend: FinancialTrend
    analysis: CompanyAnalysis
