from datetime import date

from app.models.company import CompanyDetail
from app.models.edinet import EdinetDocument
from app.models.financial import (
    FinancialHistory,
    FinancialYearValue,
)
from app.models.financial_question import (
    FinancialQuestionPlan,
)
from app.models.research import CompanyResearchResult
from app.services.company_financial import (
    CompanyFinancialService,
)


def make_research() -> CompanyResearchResult:
    return CompanyResearchResult.model_construct(
        company=CompanyDetail.model_construct(
            name="テスト株式会社",
        ),
        annual_report=EdinetDocument.model_construct(
            period_end=date(2026, 3, 31),
        ),
    )


def make_financial_value(
    *,
    value: int,
    context_id: str,
    relative_year: str,
) -> FinancialYearValue:
    return FinancialYearValue.model_construct(
        value=value,
        context_id=context_id,
        relative_year=relative_year,
    )


def make_history() -> FinancialHistory:
    return FinancialHistory.model_construct(
        revenue=[
            make_financial_value(
                value=100_000_000,
                context_id="Prior4YearDuration",
                relative_year="四期前",
            ),
            make_financial_value(
                value=300_000_000,
                context_id="Prior3YearDuration",
                relative_year="三期前",
            ),
            make_financial_value(
                value=200_000_000,
                context_id="Prior2YearDuration",
                relative_year="前々期",
            ),
            make_financial_value(
                value=250_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            make_financial_value(
                value=280_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
        operating_income=[],
        net_income=[],
        total_assets=[],
        operating_cash_flow=[],
    )


def test_company_financial_max() -> None:
    service = CompanyFinancialService()

    result = service.answer(
        research=make_research(),
        history=make_history(),
        plan=FinancialQuestionPlan(
            metric="revenue",
            operation="max",
            years=5,
        ),
    )

    assert result.insufficient_context is False
    assert result.answer == (
        "テスト株式会社の売上高は、"
        "2023年3月期の3億円です。"
    )


def test_company_financial_current() -> None:
    service = CompanyFinancialService()

    result = service.answer(
        research=make_research(),
        history=make_history(),
        plan=FinancialQuestionPlan(
            metric="revenue",
            operation="current",
        ),
    )

    assert result.insufficient_context is False
    assert result.answer == (
        "テスト株式会社の売上高は、"
        "2026年3月期の2億8,000万円です。"
    )


def test_company_financial_insufficient_periods() -> None:
    service = CompanyFinancialService()

    result = service.answer(
        research=make_research(),
        history=make_history(),
        plan=FinancialQuestionPlan(
            metric="revenue",
            operation="max",
            years=10,
        ),
    )

    assert result.insufficient_context is True
    assert result.answer == (
        "現在取得できている売上高は"
        "5期分のため、"
        "過去10期については"
        "判定できません。"
    )


def test_company_financial_available_periods() -> None:
    service = CompanyFinancialService()

    result = service.answer(
        research=make_research(),
        history=make_history(),
        plan=FinancialQuestionPlan(
            metric=None,
            operation="available_periods",
        ),
    )

    assert result.insufficient_context is False
    assert result.answer == (
        "現在取得できる財務履歴は"
        "最大5期分です。"
        "指標によって取得できる期数が"
        "異なる場合があります。"
    )

def test_answer_overall_performance() -> None:
    service = CompanyFinancialService()

    research = CompanyResearchResult.model_construct(
        company=CompanyDetail.model_construct(
            name="テスト株式会社",
        ),
        annual_report=EdinetDocument.model_construct(
            period_end=date(2026, 3, 31),
        ),
    )

    history = FinancialHistory.model_construct(
        revenue=[
            FinancialYearValue.model_construct(
                value=100_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            FinancialYearValue.model_construct(
                value=120_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
        operating_income=[
            FinancialYearValue.model_construct(
                value=10_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            FinancialYearValue.model_construct(
                value=15_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
         ordinary_income=[
            FinancialYearValue.model_construct(
                value=9_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            FinancialYearValue.model_construct(
                value=14_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
        profit_before_tax=[
            FinancialYearValue.model_construct(
                value=9_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            FinancialYearValue.model_construct(
                value=14_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
        net_income=[
            FinancialYearValue.model_construct(
                value=6_000_000,
                context_id="Prior1YearDuration",
                relative_year="前期",
            ),
            FinancialYearValue.model_construct(
                value=10_000_000,
                context_id="CurrentYearDuration",
                relative_year="当期",
            ),
        ],
        total_assets=[],
        operating_cash_flow=[],
    )

    plan = FinancialQuestionPlan(
        metric=None,
        operation="current",
        years=5,
        is_overall_performance=True,
    )

    result = service.answer(
        research=research,
        history=history,
        plan=plan,
    )

    assert result.insufficient_context is False
    assert "テスト株式会社" in result.answer
    assert "売上高" in result.answer
    assert "営業利益" in result.answer
    assert "経常利益" in result.answer
    assert "純利益" in result.answer
    assert "2025年3月期" in result.answer
    assert "2026年3月期" in result.answer