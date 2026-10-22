import asyncio
from dataclasses import dataclass

from app.repositories.databricks_document_chunk import (
    DatabricksDocumentChunkRepository,
)
from app.repositories.databricks_edinet_document import (
    DatabricksEdinetDocumentRepository,
)
from app.services.company_research import (
    CompanyResearchService,
)
from app.services.document_chunking import (
    DocumentChunkingService,
)
from app.services.document_indexing import (
    DocumentIndexingService,
)


@dataclass(frozen=True)
class ChunkConfig:
    chunk_size: int
    overlap: int
    table_basename: str


COMPANIES = [
    "任天堂",
    "トヨタ自動車",
    "ファーストリテイリング",
]

CONFIGS = [
    ChunkConfig(
        chunk_size=500,
        overlap=100,
        table_basename=(
            "edinet_document_chunks_500_100"
        ),
    ),
    ChunkConfig(
        chunk_size=1_500,
        overlap=200,
        table_basename=(
            "edinet_document_chunks_1500_200"
        ),
    ),
]


async def main() -> None:
    research_repository = (
        DatabricksEdinetDocumentRepository()
    )

    research_service = CompanyResearchService(
        research_repository
    )

    for config in CONFIGS:
        print()
        print(
            "=== "
            f"{config.chunk_size}/"
            f"{config.overlap} "
            "==="
        )

        chunk_repository = (
            DatabricksDocumentChunkRepository(
                table_basename=(
                    config.table_basename
                ),
            )
        )

        indexing_service = (
            DocumentIndexingService(
                repository=chunk_repository,
                chunking_service=(
                    DocumentChunkingService(
                        chunk_size=(
                            config.chunk_size
                        ),
                        overlap=config.overlap,
                    )
                ),
            )
        )

        for company_name in COMPANIES:
            research = (
                await research_service.research(
                    name=company_name
                )
            )

            chunks = (
                indexing_service
                .index_company_research(
                    research
                )
            )

            business_overview_count = sum(
                chunk.section
                == "business_overview"
                for chunk in chunks
            )

            business_risks_count = sum(
                chunk.section
                == "business_risks"
                for chunk in chunks
            )

            print(
                f"{company_name}: "
                f"{len(chunks)} chunks "
                "("
                f"overview="
                f"{business_overview_count}, "
                f"risks="
                f"{business_risks_count}"
                ")"
            )


if __name__ == "__main__":
    asyncio.run(main())