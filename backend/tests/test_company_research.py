from app.services.company_research import (
    build_company_search_names,
)


def test_build_company_search_names_without_corporate_type() -> None:
    assert build_company_search_names(
        "ヘッドウォータース"
    ) == [
        "ヘッドウォータース",
    ]


def test_build_company_search_names_with_prefix() -> None:
    assert build_company_search_names(
        "株式会社ヘッドウォータース"
    ) == [
        "株式会社ヘッドウォータース",
        "ヘッドウォータース",
    ]


def test_build_company_search_names_with_suffix() -> None:
    assert build_company_search_names(
        "ヘッドウォータース株式会社"
    ) == [
        "ヘッドウォータース株式会社",
        "ヘッドウォータース",
    ]