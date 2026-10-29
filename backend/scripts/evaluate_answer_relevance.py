import asyncio
from pathlib import Path

from agents import set_default_openai_key

from app.services.answer_relevance_evaluation import (
    AnswerRelevanceEvaluationService,
)
from app.settings import get_settings


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    service = AnswerRelevanceEvaluationService()

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "answer_relevance_cases.json"
    )

    cases = service.load_cases(
        cases_path,
    )

    passed_count = 0

    for case in cases:
        result = await service.evaluate(
            question=case.question,
            answer=case.answer,
        )

        passed = (
            result.relevant
            == case.expected_relevant
        )

        if passed:
            passed_count += 1

        print()
        print("=" * 80)
        print(f"id: {case.id}")
        print(f"question: {case.question}")
        print(f"answer: {case.answer}")

        print(
            "expected_relevant:",
            case.expected_relevant,
        )

        print(
            "actual_relevant:",
            result.relevant,
        )

        print(
            "reason:",
            result.reason,
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


if __name__ == "__main__":
    asyncio.run(main())