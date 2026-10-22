import asyncio

from agents import set_default_openai_key

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


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    question = (
        "任天堂のサイバー攻撃による"
        "事業へのリスクは？"
    )

    planner = DocumentQueryPlanningService()

    plan = await planner.plan(
        question
    )

    repository = (
        DatabricksDocumentSearchRepository(
            endpoint_name=(
                "ai-project-assistant-search"
            ),
        )
    )

    chunks = repository.search(
        query_text=plan.query_text,
        edinet_code="E02367",
        doc_id="S100Y9NX",
        num_results=3,
    )

    answering_service = (
        DocumentAnsweringService()
    )

    answer = await answering_service.answer(
        question=question,
        chunks=chunks,
    )

    print(f"question: {question}")
    print(f"query: {plan.query_text}")
    print()

    print("retrieved:")
    for rank, chunk in enumerate(
        chunks,
        start=1,
    ):
        print(
            f"{rank}: "
            f"{chunk.chunk_id} "
            f"score={chunk.score:.4f}"
        )

    print()
    print(f"answer: {answer.answer}")
    print(
        "evidence_chunk_ids: "
        f"{answer.evidence_chunk_ids}"
    )
    print(
        "insufficient_context: "
        f"{answer.insufficient_context}"
    )


if __name__ == "__main__":
    asyncio.run(main())