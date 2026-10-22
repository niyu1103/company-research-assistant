import asyncio

from agents import set_default_openai_key

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
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
        "任天堂のサイバー攻撃による事業へのリスクは？"
    )

    query_planner = DocumentQueryPlanningService()

    plan = await query_planner.plan(
        question
    )

    print(f"question: {question}")
    print(f"query_text: {plan.query_text}")
    print()

    repository = DatabricksDocumentSearchRepository(
        endpoint_name="ai-project-assistant-search",
    )

    chunks = repository.search(
        query_text=plan.query_text,
        edinet_code="E02367",
        doc_id="S100Y9NX",
        num_results=5,
    )

    for rank, chunk in enumerate(chunks, start=1):
        print(
            f"{rank}: "
            f"{chunk.chunk_id} "
            f"score={chunk.score}"
        )


if __name__ == "__main__":
    asyncio.run(main())