from datetime import UTC, datetime

from app.models.document_freshness import (
    DocumentIndexState,
)
from app.repositories.document_index_state import (
    DocumentIndexStateRepository,
)
from app.repositories.document_index_sync import (
    DocumentIndexSyncRepository,
)


class DocumentIndexSyncService:
    def __init__(
        self,
        *,
        sync_repository: DocumentIndexSyncRepository,
        state_repository: DocumentIndexStateRepository,
    ) -> None:
        self.sync_repository = sync_repository
        self.state_repository = state_repository

    def sync(
        self,
        *,
        doc_id: str,
        version: str,
    ) -> DocumentIndexState:
        self.sync_repository.sync_and_wait()

        state = DocumentIndexState(
            doc_id=doc_id,
            version=version,
            indexed_at=datetime.now(UTC),
        )

        self.state_repository.save(state)

        return state
