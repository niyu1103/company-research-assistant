from pydantic import BaseModel, Field


class FinancialMetric(BaseModel):
    value: int
    unit: str | None = None
    element_id: str
    item_name: str | None = None
    context_id: str
    relative_year: str | None = None


class FinancialSummary(BaseModel):
    doc_id: str

    revenue: FinancialMetric | None = None
    operating_income: FinancialMetric | None = None
    profit_before_tax: FinancialMetric | None = None
    net_income: FinancialMetric | None = None
    total_assets: FinancialMetric | None = None
    operating_cash_flow: FinancialMetric | None = None


class FinancialYearValue(BaseModel):
    relative_year: str
    context_id: str
    value: int
    unit: str | None = None


class FinancialHistory(BaseModel):
    revenue: list[FinancialYearValue] = Field(default_factory=list)
    operating_income: list[FinancialYearValue] = Field(default_factory=list)
    profit_before_tax: list[FinancialYearValue] = Field(default_factory=list)
    net_income: list[FinancialYearValue] = Field(default_factory=list)
    total_assets: list[FinancialYearValue] = Field(default_factory=list)
    operating_cash_flow: list[FinancialYearValue] = Field(default_factory=list)
    ordinary_income: list[FinancialYearValue] = Field(default_factory=list)


class FinancialTrendYear(BaseModel):
    relative_year: str

    revenue: int | None = None
    operating_income: int | None = None
    profit_before_tax: int | None = None
    net_income: int | None = None
    total_assets: int | None = None
    operating_cash_flow: int | None = None

    revenue_growth_rate: float | None = None
    operating_income_growth_rate: float | None = None
    net_income_growth_rate: float | None = None

    operating_margin: float | None = None
    net_margin: float | None = None
    operating_cash_flow_margin: float | None = None


class FinancialTrend(BaseModel):
    years: list[FinancialTrendYear] = Field(default_factory=list)
