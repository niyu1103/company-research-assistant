import asyncio
from pathlib import Path

from app.main import company_document_qa_service
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
from app.services.document_retrieval import DocumentRetrievalService


async def main() -> None:
    context_sufficiency_service = (
        ContextSufficiencyEvaluationService()
    )

    research_service = CompanyResearchService(
        DatabricksEdinetDocumentRepository(),
    )

    query_planning_service = (
        DocumentQueryPlanningService()
    )

    retrieval_service = DocumentRetrievalService(
        repository=DatabricksDocumentSearchRepository(
            endpoint_name="ai-project-assistant-search",
        ),
    )

    cases_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "context_sufficiency_cases.json"
    )

    cases = context_sufficiency_service.load_cases(
        cases_path,
    )

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

        sufficiency_result = (
            await context_sufficiency_service.evaluate(
                question=case.question,
                chunks=chunks,
            )
        )

        qa_result = (
            await company_document_qa_service.answer(
                name=case.company_name,
                question=case.question,
            )
        )

        expected_insufficient_context = (
            not sufficiency_result.sufficient
        )

        actual_insufficient_context = (
            qa_result.insufficient_context
        )

        passed = (
            expected_insufficient_context
            == actual_insufficient_context
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
        print(
            "golden_sufficient:",
            case.expected_sufficient,
        )
        print(
            "judge_sufficient:",
            sufficiency_result.sufficient,
        )
        print(
            "expected_insufficient_context:",
            expected_insufficient_context,
        )
        print(
            "actual_insufficient_context:",
            actual_insufficient_context,
        )
        print(
            f"answer: {qa_result.answer}"
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