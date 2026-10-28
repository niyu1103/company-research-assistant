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

    retrieval_evaluation_service = (
        RetrievalEvaluationService()
    )

    groundedness_evaluation_service = (
        GroundednessEvaluationService()
    )

    cases = retrieval_evaluation_service.load_cases(
        Path("evals/retrieval_cases.json"),
    )

    if not cases:
        raise ValueError(
            "Retrieval evaluation cases are empty."
        )

    recall_at_1_values: list[float] = []
    precision_at_1_values: list[float] = []
    recall_at_3_values: list[float] = []
    precision_at_3_values: list[float] = []
    reciprocal_rank_values: list[float] = []

    groundedness_scores: list[float] = []
    groundedness_passed_count = 0

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

        retrieved_chunk_ids = [
            chunk.chunk_id
            for chunk in chunks
        ]

        top_1_metrics = (
            retrieval_evaluation_service.calculate_metrics(
                expected_chunk_ids=case.expected_chunk_ids,
                retrieved_chunk_ids=retrieved_chunk_ids,
                k=1,
            )
        )

        top_3_metrics = (
            retrieval_evaluation_service.calculate_metrics(
                expected_chunk_ids=case.expected_chunk_ids,
                retrieved_chunk_ids=retrieved_chunk_ids,
                k=3,
            )
        )

        recall_at_1_values.append(
            top_1_metrics.recall_at_k,
        )
        precision_at_1_values.append(
            top_1_metrics.precision_at_k,
        )
        recall_at_3_values.append(
            top_3_metrics.recall_at_k,
        )
        precision_at_3_values.append(
            top_3_metrics.precision_at_k,
        )
        reciprocal_rank_values.append(
            top_3_metrics.reciprocal_rank,
        )

        answer_result = await answering_service.answer(
            question=case.question,
            chunks=chunks,
        )

        groundedness = (
            await groundedness_evaluation_service.evaluate(
                question=case.question,
                answer=answer_result.answer,
                chunks=chunks,
            )
        )

        groundedness_scores.append(
            groundedness.score,
        )

        if groundedness.passed:
            groundedness_passed_count += 1

        print()
        print("=" * 80)
        print(f"case: {case.id}")
        print(f"company: {case.company_name}")
        print(f"question: {case.question}")
        print(f"query_text: {query_plan.query_text}")

        print()
        print("expected_chunk_ids:")
        for chunk_id in case.expected_chunk_ids:
            print(f"- {chunk_id}")

        print()
        print("retrieved_chunk_ids:")
        for rank, chunk in enumerate(
            chunks,
            start=1,
        ):
            print(
                f"{rank}. "
                f"{chunk.chunk_id} "
                f"score={chunk.score}"
            )

        print()
        print("RETRIEVAL")
        print(
            f"recall@1: "
            f"{top_1_metrics.recall_at_k:.3f}"
        )
        print(
            f"precision@1: "
            f"{top_1_metrics.precision_at_k:.3f}"
        )
        print(
            f"recall@3: "
            f"{top_3_metrics.recall_at_k:.3f}"
        )
        print(
            f"precision@3: "
            f"{top_3_metrics.precision_at_k:.3f}"
        )
        print(
            f"reciprocal_rank: "
            f"{top_3_metrics.reciprocal_rank:.3f}"
        )

        print()
        print("ANSWER")
        print(answer_result.answer)

        print()
        print("GROUNDEDNESS")
        print(
            f"score: "
            f"{groundedness.score:.3f}"
        )
        print(
            f"passed: "
            f"{groundedness.passed}"
        )
        print(
            f"claims: "
            f"{len(groundedness.claims)}"
        )

        for claim in groundedness.claims:
            status = (
                "SUPPORTED"
                if claim.supported
                else "UNSUPPORTED"
            )

            print(
                f"- [{status}] "
                f"{claim.claim}"
            )

    print()
    print("=" * 80)
    print("RAG EVALUATION SUMMARY")
    print()
    print(f"cases: {len(cases)}")

    print()
    print("RETRIEVAL")
    print(
        "mean_recall@1: "
        f"{fmean(recall_at_1_values):.3f}"
    )
    print(
        "mean_precision@1: "
        f"{fmean(precision_at_1_values):.3f}"
    )
    print(
        "mean_recall@3: "
        f"{fmean(recall_at_3_values):.3f}"
    )
    print(
        "mean_precision@3: "
        f"{fmean(precision_at_3_values):.3f}"
    )
    print(
        "mrr@3: "
        f"{fmean(reciprocal_rank_values):.3f}"
    )

    print()
    print("GROUNDEDNESS")
    print(
        "mean_groundedness: "
        f"{fmean(groundedness_scores):.3f}"
    )
    print(
        "pass_rate: "
        f"{groundedness_passed_count / len(cases):.3f}"
    )
    print(
        "passed_cases: "
        f"{groundedness_passed_count}/{len(cases)}"
    )


if __name__ == "__main__":
    asyncio.run(main())