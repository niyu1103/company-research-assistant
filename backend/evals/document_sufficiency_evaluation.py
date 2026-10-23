import asyncio
from pathlib import Path

from agents import set_default_openai_key
from pydantic import BaseModel, TypeAdapter

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.services.document_answering import (
    DocumentAnsweringService,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.settings import get_settings


class ConfidenceCase(BaseModel):
    question: str
    edinet_code: str
    doc_id: str
    expect_insufficient_context: bool


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    cases_path = (
        Path(__file__).parent
        / "document_confidence_cases.json"
    )

    cases = TypeAdapter(
        list[ConfidenceCase]
    ).validate_json(
        cases_path.read_text(
            encoding="utf-8"
        )
    )

    planner = DocumentQueryPlanningService()

    repository = (
        DatabricksDocumentSearchRepository(
            endpoint_name=(
                "ai-project-assistant-search"
            ),
        )
    )

    answering = DocumentAnsweringService()

    correct_count = 0

    for case_index, case in enumerate(
        cases,
        start=1,
    ):
        plan = await planner.plan(
            case.question
        )

        chunks = repository.search(
            query_text=plan.query_text,
            edinet_code=case.edinet_code,
            doc_id=case.doc_id,
            num_results=3,
        )

        answer = await answering.answer(
            question=case.question,
            chunks=chunks,
        )

        actual = (
            answer.insufficient_context
        )

        matched = (
            actual
            == case.expect_insufficient_context
        )

        if matched:
            correct_count += 1

        top_score = (
            chunks[0].score
            if chunks
            else 0.0
        )

        expected_label = (
            "INSUFFICIENT"
            if case.expect_insufficient_context
            else "ANSWERABLE"
        )

        actual_label = (
            "INSUFFICIENT"
            if actual
            else "ANSWERABLE"
        )

        print()
        print(
            f"=== Case {case_index} ==="
        )
        print(
            f"Question: {case.question}"
        )
        print(
            f"Query: {plan.query_text}"
        )
        print(
            f"Top1 score: {top_score:.4f}"
        )
        print(
            f"Expected: {expected_label}"
        )
        print(
            f"Actual:   {actual_label}"
        )
        print(
            f"Match: {matched}"
        )
        print(
            f"Evidence: "
            f"{answer.evidence_chunk_ids}"
        )
        print(
            f"Answer: {answer.answer}"
        )

    accuracy = (
        correct_count / len(cases)
        if cases
        else 0.0
    )

    print()
    print(
        "================================"
    )
    print(
        "Context Sufficiency Evaluation"
    )
    print(
        "================================"
    )
    print(
        f"Accuracy: {accuracy:.2%}"
    )
    print(
        f"Correct: {correct_count}/{len(cases)}"
    )


if __name__ == "__main__":
    asyncio.run(main())