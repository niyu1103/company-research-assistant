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


RUN_COUNT = 3


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

    question = (
        "情報システム障害やクラウドサービス停止について、"
        "どのようなリスクがありますか？"
    )

    research = await research_service.research(
        name="株式会社ヘッドウォータース",
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

    print("=" * 80)
    print("ANSWER")
    print(answer_result.answer)

    for run_number in range(1, RUN_COUNT + 1):
        evaluation = await evaluation_service.evaluate(
            question=question,
            answer=answer_result.answer,
            chunks=chunks,
        )

        print()
        print("=" * 80)
        print(f"RUN {run_number}")
        print(f"score: {evaluation.score:.3f}")
        print(f"passed: {evaluation.passed}")
        print(f"claims: {len(evaluation.claims)}")

        for claim in evaluation.claims:
            status = "SUPPORTED" if claim.supported else "UNSUPPORTED"

            print(
                f"- [{status}] "
                f"{claim.claim}"
            )

        print(
            "unsupported_claims:",
            evaluation.unsupported_claims,
        )


if __name__ == "__main__":
    asyncio.run(main())