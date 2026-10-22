from typing import Protocol

from app.models.document_chunk import RetrievedDocumentChunk


class DocumentSearchRepository(Protocol):
    def search(
        self,
        *,
        query_text: str,
        edinet_code: str,
        doc_id: str,
        num_results: int = 5,
    ) -> list[RetrievedDocumentChunk]: ...
