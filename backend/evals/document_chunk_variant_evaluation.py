import asyncio
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class ChunkVariant:
    label: str
    index_basename: str


@dataclass
class VariantMetrics:
    context_required_recalls: list[float] = field(
        default_factory=list
    )
    answer_required_recalls: list[float] = field(
        default_factory=list
    )
    groundedness_scores: list[float] = field(
        default_factory=list
    )
    insufficient_context_matches: list[float] = field(
        default_factory=list
    )
    retrieved_chars: list[int] = field(
        default_factory=list
    )


VARIANTS = [
    ChunkVariant(
        label="500/100",
        index_basename=(
            "edinet_document_chunks_500_100_index"
        ),
    ),
    ChunkVariant(
        label="1000/150",
        index_basename=(
            "edinet_document_chunks_index"
        ),
    ),
    ChunkVariant(
        label="1500/200",
        index_basename=(
            "edinet_document_chunks_1500_200_index"
        ),
    ),
]


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

    answering = (
        DocumentAnsweringService()
    )

    groundedness_evaluator = (
        DocumentGroundednessEvaluationService()
    )

    fact_recall_evaluator = (
        DocumentAnswerRecallEvaluationService()
    )

    plans = []

    print(
        "Planning queries..."
    )

    for case in cases:
        plan = await planner.plan(
            case.question
        )

        plans.append(plan)

    results: dict[
        str,
        VariantMetrics,
    ] = {}

    for variant in VARIANTS:
        print()
        print(
            "================================"
        )
        print(
            f"Variant: {variant.label}"
        )
        print(
            "================================"
        )

        repository = (
            DatabricksDocumentSearchRepository(
                endpoint_name=(
                    "ai-project-assistant-search"
                ),
                index_basename=(
                    variant.index_basename
                ),
            )
        )

        metrics = VariantMetrics()

        for case_index, (
            case,
            plan,
        ) in enumerate(
            zip(
                cases,
                plans,
                strict=True,
            ),
            start=1,
        ):
            chunks = repository.search(
                query_text=plan.query_text,
                edinet_code=case.edinet_code,
                doc_id=case.doc_id,
                num_results=3,
            )

            context = build_document_context(
                chunks
            )

            metrics.retrieved_chars.append(
                sum(
                    len(chunk.content)
                    for chunk in chunks
                )
            )

            context_recall = None

            if case.required_facts:
                context_recall = (
                    await fact_recall_evaluator.evaluate(
                        answer=context,
                        expected_facts=(
                            case.required_facts
                        ),
                    )
                )

                metrics.context_required_recalls.append(
                    context_recall.recall
                )

            answer = await answering.answer(
                question=case.question,
                chunks=chunks,
            )

            answer_recall = None

            if case.required_facts:
                answer_recall = (
                    await fact_recall_evaluator.evaluate(
                        answer=answer.answer,
                        expected_facts=(
                            case.required_facts
                        ),
                    )
                )

                metrics.answer_required_recalls.append(
                    answer_recall.recall
                )

            groundedness = (
                await groundedness_evaluator.evaluate(
                    answer=answer.answer,
                    context=context,
                )
            )

            metrics.groundedness_scores.append(
                groundedness.score
            )

            insufficient_context_match = (
                answer.insufficient_context
                == case.expect_insufficient_context
            )

            metrics.insufficient_context_matches.append(
                float(
                    insufficient_context_match
                )
            )

            print()
            print(
                f"Case {case_index}: "
                f"{case.question}"
            )

            print(
                f"Query: {plan.query_text}"
            )

            print(
                "Retrieved:"
            )

            for rank, chunk in enumerate(
                chunks,
                start=1,
            ):
                print(
                    f"  {rank}: "
                    f"{chunk.chunk_id} "
                    f"score={chunk.score:.4f}"
                )

            if context_recall is not None:
                print(
                    "Context Required Fact Recall@3: "
                    f"{context_recall.recall:.2f}"
                )
                print(
                    "Context missed facts: "
                    f"{context_recall.missed_fact_indices}"
                )
            else:
                print(
                    "Context Required Fact Recall@3: "
                    "N/A"
                )

            if answer_recall is not None:
                print(
                    "Answer Required Fact Recall: "
                    f"{answer_recall.recall:.2f}"
                )
                print(
                    "Answer missed facts: "
                    f"{answer_recall.missed_fact_indices}"
                )
            else:
                print(
                    "Answer Required Fact Recall: "
                    "N/A"
                )

            print(
                "Groundedness: "
                f"{groundedness.score:.2f}"
            )

            print(
                "Insufficient Context Match: "
                f"{insufficient_context_match}"
            )

            print(
                "Retrieved chars: "
                f"{metrics.retrieved_chars[-1]}"
            )

        results[
            variant.label
        ] = metrics

    print()
    print(
        "================================"
    )
    print(
        "Chunk Variant Comparison"
    )
    print(
        "================================"
    )

    for variant in VARIANTS:
        metrics = results[
            variant.label
        ]

        print()
        print(
            f"--- {variant.label} ---"
        )

        print(
            "Context Required Fact Recall@3: "
            f"{mean(metrics.context_required_recalls):.2%}"
        )

        print(
            "Answer Required Fact Recall: "
            f"{mean(metrics.answer_required_recalls):.2%}"
        )

        print(
            "Groundedness: "
            f"{mean(metrics.groundedness_scores):.2%}"
        )

        print(
            "Insufficient Context Accuracy: "
            f"{mean(metrics.insufficient_context_matches):.2%}"
        )

        print(
            "Average Retrieved Chars: "
            f"{mean(metrics.retrieved_chars):.0f}"
        )


if __name__ == "__main__":
    asyncio.run(main())