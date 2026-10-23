import asyncio
from dataclasses import dataclass
from pathlib import Path

from agents import set_default_openai_key
from pydantic import BaseModel, Field, TypeAdapter

from app.repositories.databricks_document_search import (
    DatabricksDocumentSearchRepository,
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

    repositories = {
        variant.label: (
            DatabricksDocumentSearchRepository(
                endpoint_name=(
                    "ai-project-assistant-search"
                ),
                index_basename=(
                    variant.index_basename
                ),
            )
        )
        for variant in VARIANTS
    }

    for case_index, case in enumerate(
        cases,
        start=1,
    ):
        plan = await planner.plan(
            case.question
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

        for variant in VARIANTS:
            repository = repositories[
                variant.label
            ]

            chunks = repository.search(
                query_text=plan.query_text,
                edinet_code=case.edinet_code,
                doc_id=case.doc_id,
                num_results=3,
            )

            print()
            print(
                f"--- {variant.label} ---"
            )

            for rank, chunk in enumerate(
                chunks,
                start=1,
            ):
                preview = (
                    chunk.content
                    .replace("\n", " ")
                    [:200]
                )

                print(
                    f"{rank}: "
                    f"{chunk.chunk_id} "
                    f"score={chunk.score:.4f}"
                )
                print(
                    f"   {preview}"
                )


if __name__ == "__main__":
    asyncio.run(main())