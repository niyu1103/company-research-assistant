from app.models.document_chunk import DocumentChunk
from app.models.research import CompanyResearchResult
from app.repositories.document_chunk import DocumentChunkRepository
from app.services.document_chunking import DocumentChunkingService


class DocumentIndexingService:
    def __init__(
        self,
        repository: DocumentChunkRepository,
        chunking_service: DocumentChunkingService,
    ) -> None:
        self.repository = repository
        self.chunking_service = chunking_service

    def index_company_research(
        self,
        research: CompanyResearchResult,
    ) -> list[DocumentChunk]:
        doc_id = research.annual_report.doc_id
        edinet_code = research.edinet_code

        chunks: list[DocumentChunk] = []

        chunks.extend(
            self.chunking_service.chunk_text(
                doc_id=doc_id,
                edinet_code=edinet_code,
                section="business_overview",
                text=research.narratives.business_overview,
            )
        )

        chunks.extend(
            self.chunking_service.chunk_text(
                doc_id=doc_id,
                edinet_code=edinet_code,
                section="business_risks",
                text=research.narratives.business_risks,
            )
        )

        self.repository.replace_for_document(
            doc_id=doc_id,
            chunks=chunks,
        )

        return chunks
