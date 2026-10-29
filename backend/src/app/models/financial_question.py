from typing import Literal

from pydantic import BaseModel, Field

FinancialMetric = Literal[
    "revenue",
    "operating_income",
    "net_income",
    "total_assets",
    "operating_cash_flow",
]

FinancialOperation = Literal[
    "current",
    "max",
    "min",
    "available_periods",
]


class FinancialQuestionPlan(BaseModel):
    metric: FinancialMetric | None = None
    operation: FinancialOperation
    years: int | None = Field(
        default=None,
        ge=1,
    )

    requires_specific_period: bool = False
    period_hint: str | None = None

    is_overall_performance: bool = False


class FinancialQuestionAnswer(BaseModel):
    answer: str
    insufficient_context: bool
