from app.models.document_chunk import RetrievedDocumentChunk
from app.models.research import CompanyResearchResult
from app.repositories.document_search import DocumentSearchRepository


class DocumentRetrievalService:
    def __init__(
        self,
        repository: DocumentSearchRepository,
    ) -> None:
        self.repository = repository

    def retrieve(
        self,
        *,
        research: CompanyResearchResult,
        query_text: str,
        num_results: int = 5,
    ) -> list[RetrievedDocumentChunk]:
        query_text = query_text.strip()

        if not query_text:
            return []

        return self.repository.search(
            query_text=query_text,
            edinet_code=research.edinet_code,
            doc_id=research.annual_report.doc_id,
            num_results=num_results,
        )
