import asyncio

from agents import set_default_openai_key

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_research import CompanyResearchService
from app.services.document_answering import DocumentAnsweringService
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.services.document_retrieval import DocumentRetrievalService
from app.services.groundedness_evaluation import (
    GroundednessEvaluationService,
)
from app.settings import get_settings


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    research_service = CompanyResearchService(
        DatabricksEdinetDocumentRepository(),
    )

    query_planning_service = DocumentQueryPlanningService()

    retrieval_service = DocumentRetrievalService(
        repository=DatabricksDocumentSearchRepository(
            endpoint_name="ai-project-assistant-search",
        ),
    )

    answering_service = DocumentAnsweringService()
    evaluation_service = GroundednessEvaluationService()

    company_name = "株式会社ヘッドウォータース"

    question = (
        "情報システム障害やクラウドサービス停止について、"
        "どのようなリスクがありますか？"
    )

    research = await research_service.research(
        name=company_name,
    )

    query_plan = await query_planning_service.plan(
        question,
    )

    chunks = retrieval_service.retrieve(
        research=research,
        query_text=query_plan.query_text,
        num_results=3,
    )

    answer_result = await answering_service.answer(
        question=question,
        chunks=chunks,
    )

    normal_evaluation = await evaluation_service.evaluate(
        question=question,
        answer=answer_result.answer,
        chunks=chunks,
    )

    unsupported_answer = (
        answer_result.answer
        + " また、この障害が発生した場合、"
        "売上高が30％減少するとされています。"
    )

    unsupported_evaluation = await evaluation_service.evaluate(
        question=question,
        answer=unsupported_answer,
        chunks=chunks,
    )

    print("=" * 80)
    print("RETRIEVED CHUNKS")

    for rank, chunk in enumerate(chunks, start=1):
        print(
            f"{rank}. "
            f"{chunk.chunk_id} "
            f"score={chunk.score}"
        )

    print()
    print("=" * 80)
    print("NORMAL ANSWER")
    print(answer_result.answer)

    print()
    print("Groundedness:")
    print(
        normal_evaluation.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("=" * 80)
    print("UNSUPPORTED ANSWER")
    print(unsupported_answer)

    print()
    print("Groundedness:")
    print(
        unsupported_evaluation.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())