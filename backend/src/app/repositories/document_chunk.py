from typing import Protocol

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository(Protocol):
    def create_table(self) -> None: ...

    def replace_for_document(
        self,
        doc_id: str,
        chunks: list[DocumentChunk],
    ) -> None: ...
