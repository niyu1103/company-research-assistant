from pydantic import BaseModel


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
