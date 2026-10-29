import asyncio
from pathlib import Path

from agents import set_default_openai_key

from app.models.research import CompanyResearchResult
from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_research import CompanyResearchService
from app.services.context_sufficiency_evaluation import (
    ContextSufficiencyEvaluationService,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.services.document_retrieval import (
    DocumentRetrievalService,
)
from app.settings import get_settings


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    evaluation_service = (
        ContextSufficiencyEvaluationService()
    )

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "context_sufficiency_cases.json"
    )

    cases = evaluation_service.load_cases(
        cases_path,
    )

    research_service = CompanyResearchService(
        DatabricksEdinetDocumentRepository(),
    )

    retrieval_service = DocumentRetrievalService(
        repository=DatabricksDocumentSearchRepository(
            endpoint_name="ai-project-assistant-search",
        ),
    )

    query_planning_service = (
        DocumentQueryPlanningService()
    )

    research_cache: dict[
        str,
        CompanyResearchResult,
    ] = {}

    passed_count = 0

    for case in cases:
        research = research_cache.get(
            case.company_name
        )

        if research is None:
            research = await research_service.research(
                name=case.company_name,
            )

            research_cache[
                case.company_name
            ] = research

        query_plan = await query_planning_service.plan(
            case.question,
        )

        chunks = retrieval_service.retrieve(
            research=research,
            query_text=query_plan.query_text,
            num_results=3,
        )

        result = await evaluation_service.evaluate(
            question=case.question,
            chunks=chunks,
        )

        passed = (
            result.sufficient
            == case.expected_sufficient
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
            f"query_text: {query_plan.query_text}"
        )

        print("retrieved_chunks:")

        for chunk in chunks:
            print(
                f"  - {chunk.chunk_id}"
                f" score={chunk.score:.4f}"
            )

        print(
            "expected_sufficient:",
            case.expected_sufficient,
        )

        print(
            "actual_sufficient:",
            result.sufficient,
        )

        print(
            "evidence_chunk_ids:",
            result.evidence_chunk_ids,
        )

        print(
            "missing_information:",
            result.missing_information,
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
    
    if passed_count != total:
     raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())