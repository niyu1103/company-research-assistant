import asyncio
from pathlib import Path
from statistics import mean

from agents import set_default_openai_key
from pydantic import BaseModel, Field, TypeAdapter

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.settings import get_settings


class RetrievalEvalCase(BaseModel):
    question: str
    edinet_code: str
    doc_id: str
    expected_chunk_ids: list[str] = Field(
        min_length=1
    )


def recall_at_k(
    *,
    retrieved_ids: list[str],
    expected_ids: list[str],
    k: int,
) -> float:
    retrieved = set(retrieved_ids[:k])
    expected = set(expected_ids)

    return len(retrieved & expected) / len(expected)


def reciprocal_rank(
    *,
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> float:
    expected = set(expected_ids)

    for rank, chunk_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if chunk_id in expected:
            return 1 / rank

    return 0.0


async def main() -> None:
    settings = get_settings()

    set_default_openai_key(
        settings.openai_api_key,
    )

    cases_path = (
        Path(__file__).parent
        / "document_retrieval_cases.json"
    )

    cases = TypeAdapter(
        list[RetrievalEvalCase]
    ).validate_json(
        cases_path.read_text(
            encoding="utf-8"
        )
    )

    planner = DocumentQueryPlanningService()

    repository = DatabricksDocumentSearchRepository(
        endpoint_name="ai-project-assistant-search",
    )

    recall_1_scores: list[float] = []
    recall_3_scores: list[float] = []
    recall_5_scores: list[float] = []
    reciprocal_ranks: list[float] = []

    for index, case in enumerate(
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
            num_results=5,
        )

        retrieved_ids = [
            chunk.chunk_id
            for chunk in chunks
        ]

        recall_1 = recall_at_k(
            retrieved_ids=retrieved_ids,
            expected_ids=case.expected_chunk_ids,
            k=1,
        )
        recall_3 = recall_at_k(
            retrieved_ids=retrieved_ids,
            expected_ids=case.expected_chunk_ids,
            k=3,
        )
        recall_5 = recall_at_k(
            retrieved_ids=retrieved_ids,
            expected_ids=case.expected_chunk_ids,
            k=5,
        )
        rr = reciprocal_rank(
            retrieved_ids=retrieved_ids,
            expected_ids=case.expected_chunk_ids,
        )

        recall_1_scores.append(recall_1)
        recall_3_scores.append(recall_3)
        recall_5_scores.append(recall_5)
        reciprocal_ranks.append(rr)

        print()
        print(f"=== Case {index} ===")
        print(
            f"Question: {case.question}"
        )
        print(
            f"Generated query: {plan.query_text}"
        )
        print(
            "Expected: "
            f"{case.expected_chunk_ids}"
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

        print(
            f"Recall@1: {recall_1:.2f}"
        )
        print(
            f"Recall@3: {recall_3:.2f}"
        )
        print(
            f"Recall@5: {recall_5:.2f}"
        )
        print(
            f"Reciprocal Rank: {rr:.2f}"
        )

    print()
    print("=== Overall ===")
    print(
        "Recall@1: "
        f"{mean(recall_1_scores):.2%}"
    )
    print(
        "Recall@3: "
        f"{mean(recall_3_scores):.2%}"
    )
    print(
        "Recall@5: "
        f"{mean(recall_5_scores):.2%}"
    )
    print(
        "MRR: "
        f"{mean(reciprocal_ranks):.4f}"
    )


if __name__ == "__main__":
    asyncio.run(main())