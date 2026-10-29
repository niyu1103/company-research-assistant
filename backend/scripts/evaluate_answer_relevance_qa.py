import asyncio
from pathlib import Path

from app.main import company_document_qa_service
from app.services.answer_relevance_evaluation import (
    AnswerRelevanceEvaluationService,
)


async def main() -> None:
    evaluation_service = (
        AnswerRelevanceEvaluationService()
    )

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "answer_relevance_qa_cases.json"
    )

    cases = evaluation_service.load_qa_cases(
        cases_path,
    )

    passed_count = 0

    for case in cases:
        qa_result = (
            await company_document_qa_service.answer(
                name=case.company_name,
                question=case.question,
            )
        )

        relevance_result = (
            await evaluation_service.evaluate(
                question=case.question,
                answer=qa_result.answer,
            )
        )

        passed = (
            relevance_result.relevant
            == case.expected_relevant
        )

        if passed:
            passed_count += 1

        print()
        print("=" * 80)
        print(f"id: {case.id}")
        print(
            f"company: {case.company_name}"
        )
        print(
            f"question: {case.question}"
        )
        print(
            f"query_text: {qa_result.query_text}"
        )
        print(
            f"answer: {qa_result.answer}"
        )
        print(
            "insufficient_context:",
            qa_result.insufficient_context,
        )
        print(
            "expected_relevant:",
            case.expected_relevant,
        )
        print(
            "actual_relevant:",
            relevance_result.relevant,
        )
        print(
            "reason:",
            relevance_result.reason,
        )
        print(
            "result:",
            "PASS" if passed else "FAIL",
        )

    total = len(cases)

    accuracy = (
        passed_count / total
        if total
        else 0.0
    )

    print()
    print("=" * 80)
    print("SUMMARY")
    print(f"cases: {total}")
    print(
        f"passed: {passed_count}/{total}"
    )
    print(
        f"accuracy: {accuracy:.3f}"
    )

    if passed_count != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())