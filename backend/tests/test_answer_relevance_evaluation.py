from pathlib import Path

from app.services.answer_relevance_evaluation import (
    AnswerRelevanceEvaluationService,
)


def test_load_answer_relevance_cases() -> None:
    service = AnswerRelevanceEvaluationService()

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "answer_relevance_cases.json"
    )

    cases = service.load_cases(
        cases_path,
    )

    assert len(cases) == 4

    assert (
        cases[0].id
        == "nintendo-company-culture-good-fallback"
    )

    assert cases[0].expected_relevant is True

    assert (
        cases[1].id
        == "nintendo-company-culture-direct-but-unsupported"
    )

    assert cases[1].expected_relevant is True


def test_load_answer_relevance_qa_cases() -> None:
    service = AnswerRelevanceEvaluationService()

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "answer_relevance_qa_cases.json"
    )

    cases = service.load_qa_cases(
        cases_path,
    )

    assert len(cases) == 5

    assert (
        cases[0].id
        == "headwaters-business-overview"
    )

    assert (
        cases[0].company_name
        == "株式会社ヘッドウォータース"
    )

    assert cases[0].expected_relevant is True