import asyncio
from pathlib import Path

from agents import set_default_openai_key
from pydantic import BaseModel, TypeAdapter

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
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

        top_score = (
            chunks[0].score
            if chunks
            else 0.0
        )

        label = (
            "INSUFFICIENT"
            if case.expect_insufficient_context
            else "ANSWERABLE"
        )

        print()
        print(
            f"=== Case {case_index} ==="
        )
        print(
            f"Expected: {label}"
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

        for rank, chunk in enumerate(
            chunks,
            start=1,
        ):
            print(
                f"{rank}: "
                f"{chunk.chunk_id} "
                f"score={chunk.score:.4f}"
            )


if __name__ == "__main__":
    asyncio.run(main())