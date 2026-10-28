import asyncio
from pathlib import Path

from agents import set_default_openai_key
from statistics import fmean
from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_research import CompanyResearchService
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.services.document_retrieval import DocumentRetrievalService
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

    evaluation_service = RetrievalEvaluationService()

    cases = evaluation_service.load_cases(
        Path("evals/retrieval_cases.json"),
    )
    
    recall_at_1_values: list[float] = []
    precision_at_1_values: list[float] = []
    recall_at_3_values: list[float] = []
    precision_at_3_values: list[float] = []
    reciprocal_rank_at_1_values: list[float] = []
    reciprocal_rank_at_3_values: list[float] = []

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

        top_1_metrics = evaluation_service.calculate_metrics(
            expected_chunk_ids=case.expected_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            k=1,
        )

        top_3_metrics = evaluation_service.calculate_metrics(
            expected_chunk_ids=case.expected_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            k=3,
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
        reciprocal_rank_at_1_values.append(
            top_1_metrics.reciprocal_rank,
        )
        reciprocal_rank_at_3_values.append(
            top_3_metrics.reciprocal_rank,
        )

        print()
        print("=" * 80)
        print(f"case: {case.id}")
        print(f"question: {case.question}")
        print(f"query_text: {query_plan.query_text}")
        print(f"expected: {case.expected_chunk_ids}")

        for rank, chunk in enumerate(chunks, start=1):
            print(
                f"{rank}. "
                f"{chunk.chunk_id} "
                f"score={chunk.score}"
            )

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
            f"reciprocal_rank@1: "
            f"{top_1_metrics.reciprocal_rank:.3f}"
        )
        print(
            f"reciprocal_rank@3: "
            f"{top_3_metrics.reciprocal_rank:.3f}"
        )

    print()
    print("=" * 80)
    print("SUMMARY")
    print(f"cases: {len(cases)}")
    print(
        f"mean_recall@1: "
        f"{fmean(recall_at_1_values):.3f}"
    )
    print(
        f"mean_precision@1: "
        f"{fmean(precision_at_1_values):.3f}"
    )
    print(
        f"mean_recall@3: "
        f"{fmean(recall_at_3_values):.3f}"
    )
    print(
        f"mean_precision@3: "
        f"{fmean(precision_at_3_values):.3f}"
    )
    print(
        f"mrr@1: "
        f"{fmean(reciprocal_rank_at_1_values):.3f}"
    )
    print(
        f"mrr@3: "
        f"{fmean(reciprocal_rank_at_3_values):.3f}"
    )

if __name__ == "__main__":
    asyncio.run(main())