import asyncio
from pathlib import Path
from statistics import fmean

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
from app.services.retrieval_evaluation import (
    RetrievalEvaluationService,
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
    groundedness_service = GroundednessEvaluationService()
    retrieval_evaluation_service = RetrievalEvaluationService()

    cases = retrieval_evaluation_service.load_cases(
        Path("evals/retrieval_cases.json"),
    )

    scores: list[float] = []
    passed_count = 0

    for case in cases:
        research = await research_service.research(
            name=case.company_name,
        )

        query_plan = await query_planning_service.plan(
            case.question,
        )

        chunks = retrieval_service.retrieve(
            research=research,
            query_text=query_plan.query_text,
            num_results=3,
        )

        answer_result = await answering_service.answer(
            question=case.question,
            chunks=chunks,
        )

        evaluation = await groundedness_service.evaluate(
            question=case.question,
            answer=answer_result.answer,
            chunks=chunks,
        )

        scores.append(evaluation.score)

        if evaluation.passed:
            passed_count += 1

        print()
        print("=" * 80)
        print(f"case: {case.id}")
        print(f"question: {case.question}")
        print(f"query_text: {query_plan.query_text}")
        print()
        print("answer:")
        print(answer_result.answer)
        print()
        print(f"score: {evaluation.score:.3f}")
        print(f"passed: {evaluation.passed}")
        print(f"claims: {len(evaluation.claims)}")

        for claim in evaluation.claims:
            status = (
                "SUPPORTED"
                if claim.supported
                else "UNSUPPORTED"
            )

            print(
                f"- [{status}] "
                f"{claim.claim}"
            )

        if evaluation.unsupported_claims:
            print()
            print("unsupported_claims:")

            for claim in evaluation.unsupported_claims:
                print(f"- {claim}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print(f"cases: {len(cases)}")
    print(f"mean_groundedness: {fmean(scores):.3f}")
    print(
        "pass_rate: "
        f"{passed_count / len(cases):.3f}"
    )
    print(
        f"passed_cases: "
        f"{passed_count}/{len(cases)}"
    )
    
    if passed_count != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())