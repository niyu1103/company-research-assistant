from typing import Protocol

from app.models.document_freshness import (
    DocumentIndexState,
)


class DocumentIndexStateRepository(Protocol):
    def find_by_doc_id(
        self,
        doc_id: str,
    ) -> DocumentIndexState | None: ...

    def save(
        self,
        state: DocumentIndexState,
    ) -> None: ...
