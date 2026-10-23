from app.models.company import CompanyDetail
from app.models.research import CompanyResearchResult
from app.services.company_facts import (
    CompanyFactsService,
)


def create_research() -> CompanyResearchResult:
    return CompanyResearchResult.model_construct(
        company=CompanyDetail.model_construct(
            corporate_number="1180301018771",
            name="トヨタ自動車株式会社",
            location="愛知県豊田市トヨタ町1番地",
            employee_number=1000,
            representative_name="テスト代表",
            capital_stock="1000億円",
            date_of_establishment="1937-08-28",
            founding_year=1937,
        ),
        edinet_code="E02144",
    )


def test_employee_number_is_answered_from_structured_data() -> None:
    service = CompanyFactsService()

    result = service.answer(
        research=create_research(),
        question="従業員は何人？",
    )

    assert result.fact_key == "employee_number"
    assert result.answer == (
        "トヨタ自動車株式会社の従業員数は"
        "1000人です。"
    )
    assert result.insufficient_context is False


def test_location_is_answered_from_structured_data() -> None:
    service = CompanyFactsService()

    result = service.answer(
        research=create_research(),
        question="本社はどこ？",
    )

    assert result.fact_key == "location"
    assert "愛知県豊田市トヨタ町1番地" in result.answer
    assert result.insufficient_context is False


def test_unknown_company_fact_is_insufficient() -> None:
    service = CompanyFactsService()

    result = service.answer(
        research=create_research(),
        question="好きな社食のメニューは？",
    )

    assert result.fact_key is None
    assert result.insufficient_context is True