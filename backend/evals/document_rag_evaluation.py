import asyncio
from pathlib import Path
from statistics import mean

from agents import set_default_openai_key
from pydantic import BaseModel, Field, TypeAdapter

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
)
from app.services.document_answer_recall_evaluation import (
    DocumentAnswerRecallEvaluationService,
)
from app.services.document_answering import (
    DocumentAnsweringService,
    build_document_context,
)
from app.services.document_groundedness_evaluation import (
    DocumentGroundednessEvaluationService,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.settings import get_settings


class RagEvalCase(BaseModel):
    question: str
    edinet_code: str
    doc_id: str
    expected_chunk_ids: list[str] = Field(
        default_factory=list
    )
    required_facts: list[str] = Field(
        default_factory=list
    )
    supporting_facts: list[str] = Field(
        default_factory=list
    )
    expect_insufficient_context: bool = False


def recall_at_k(
    *,
    retrieved_ids: list[str],
    expected_ids: list[str],
    k: int,
) -> float:
    if not expected_ids:
        raise ValueError(
            "expected_ids must not be empty"
        )

    retrieved = set(
        retrieved_ids[:k]
    )
    expected = set(expected_ids)

    return (
        len(retrieved & expected)
        / len(expected)
    )


def hit_at_k(
    *,
    retrieved_ids: list[str],
    expected_ids: list[str],
    k: int,
) -> float:
    if not expected_ids:
        raise ValueError(
            "expected_ids must not be empty"
        )

    retrieved = set(
        retrieved_ids[:k]
    )
    expected = set(expected_ids)

    return float(
        bool(retrieved & expected)
    )


def reciprocal_rank(
    *,
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> float:
    if not expected_ids:
        raise ValueError(
            "expected_ids must not be empty"
        )

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
        / "document_rag_cases.json"
    )

    cases = TypeAdapter(
        list[RagEvalCase]
    ).validate_json(
        cases_path.read_text(
            encoding="utf-8"
        )
    )

    planner = (
        DocumentQueryPlanningService()
    )

    repository = (
        DatabricksDocumentSearchRepository(
            endpoint_name=(
                "ai-project-assistant-search"
            ),
        )
    )

    answering = (
        DocumentAnsweringService()
    )

    groundedness_evaluator = (
        DocumentGroundednessEvaluationService()
    )

    answer_recall_evaluator = (
        DocumentAnswerRecallEvaluationService()
    )

    retrieval_hit_1: list[float] = []
    retrieval_hit_3: list[float] = []
    retrieval_recall_1: list[float] = []
    retrieval_recall_3: list[float] = []
    retrieval_mrr: list[float] = []

    required_recalls: list[float] = []
    supporting_coverages: list[float] = []
    groundedness_scores: list[float] = []
    insufficient_context_matches: list[float] = []

    for case_index, case in enumerate(
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
            num_results=3,
        )

        retrieved_ids = [
            chunk.chunk_id
            for chunk in chunks
        ]

        hit_1: float | None = None
        hit_3: float | None = None
        recall_1: float | None = None
        recall_3: float | None = None
        rr: float | None = None

        if case.expected_chunk_ids:
            hit_1 = hit_at_k(
                retrieved_ids=retrieved_ids,
                expected_ids=case.expected_chunk_ids,
                k=1,
            )

            hit_3 = hit_at_k(
                retrieved_ids=retrieved_ids,
                expected_ids=case.expected_chunk_ids,
                k=3,
            )

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

            rr = reciprocal_rank(
                retrieved_ids=retrieved_ids,
                expected_ids=case.expected_chunk_ids,
            )

            retrieval_hit_1.append(
                hit_1
            )
            retrieval_hit_3.append(
                hit_3
            )
            retrieval_recall_1.append(
                recall_1
            )
            retrieval_recall_3.append(
                recall_3
            )
            retrieval_mrr.append(
                rr
            )

        answer = await answering.answer(
            question=case.question,
            chunks=chunks,
        )

        context = build_document_context(
            chunks
        )

        groundedness = (
            await groundedness_evaluator.evaluate(
                answer=answer.answer,
                context=context,
            )
        )

        groundedness_scores.append(
            groundedness.score
        )

        insufficient_context_match = (
            answer.insufficient_context
            == case.expect_insufficient_context
        )

        insufficient_context_matches.append(
            float(insufficient_context_match)
        )

        required_recall = None

        if case.required_facts:
            required_recall = (
                await answer_recall_evaluator.evaluate(
                    answer=answer.answer,
                    expected_facts=case.required_facts,
                )
            )

            required_recalls.append(
                required_recall.recall
            )

        supporting_coverage = None

        if case.supporting_facts:
            supporting_coverage = (
                await answer_recall_evaluator.evaluate(
                    answer=answer.answer,
                    expected_facts=case.supporting_facts,
                )
            )

            supporting_coverages.append(
                supporting_coverage.recall
            )

        print()
        print(
            f"=== Case {case_index} ==="
        )
        print(
            f"Question: {case.question}"
        )
        print(
            f"Query: {plan.query_text}"
        )

        print("Retrieved:")
        for rank, chunk in enumerate(
            chunks,
            start=1,
        ):
            print(
                f"  {rank}: "
                f"{chunk.chunk_id} "
                f"score={chunk.score:.4f}"
            )

        print()
        print(
            f"Answer: {answer.answer}"
        )

        print(
            "Insufficient Context: "
            f"{answer.insufficient_context}"
        )
        print(
            "Expected Insufficient Context: "
            f"{case.expect_insufficient_context}"
        )
        print(
            "Insufficient Context Match: "
            f"{insufficient_context_match}"
        )

        print()

        if case.expected_chunk_ids:
            print(
                "Retrieval Hit@1: "
                f"{hit_1:.2f}"
            )
            print(
                "Retrieval Hit@3: "
                f"{hit_3:.2f}"
            )
            print(
                "Retrieval Recall@1: "
                f"{recall_1:.2f}"
            )
            print(
                "Retrieval Recall@3: "
                f"{recall_3:.2f}"
            )
            print(
                f"MRR: {rr:.2f}"
            )
        else:
            print(
                "Retrieval metrics: N/A "
                "(negative case)"
            )

        if required_recall is not None:
            print(
                "Required Fact Recall: "
                f"{required_recall.recall:.2f}"
            )
            print(
                "Missed required facts: "
                f"{required_recall.missed_fact_indices}"
            )
        else:
            print(
                "Required Fact Recall: N/A"
            )

        if supporting_coverage is not None:
            print(
                "Supporting Fact Coverage: "
                f"{supporting_coverage.recall:.2f}"
            )
            print(
                "Missed supporting facts: "
                f"{supporting_coverage.missed_fact_indices}"
            )

        print(
            "Groundedness: "
            f"{groundedness.score:.2f}"
        )
        print(
            "Unsupported claims: "
            f"{groundedness.unsupported_claims}"
        )

    print()
    print("=== Overall ===")

    if retrieval_hit_1:
        print(
            "Retrieval Hit@1: "
            f"{mean(retrieval_hit_1):.2%}"
        )
        print(
            "Retrieval Hit@3: "
            f"{mean(retrieval_hit_3):.2%}"
        )
        print(
            "Retrieval Recall@1: "
            f"{mean(retrieval_recall_1):.2%}"
        )
        print(
            "Retrieval Recall@3: "
            f"{mean(retrieval_recall_3):.2%}"
        )
        print(
            "MRR: "
            f"{mean(retrieval_mrr):.4f}"
        )

    if required_recalls:
        print(
            "Required Fact Recall: "
            f"{mean(required_recalls):.2%}"
        )

    if supporting_coverages:
        print(
            "Supporting Fact Coverage: "
            f"{mean(supporting_coverages):.2%}"
        )

    print(
        "Groundedness: "
        f"{mean(groundedness_scores):.2%}"
    )
    print(
        "Insufficient Context Accuracy: "
        f"{mean(insufficient_context_matches):.2%}"
    )


if __name__ == "__main__":
    asyncio.run(main())