from datetime import UTC, datetime

from app.models.document_freshness import (
    DocumentIndexState,
    DocumentIndexUpdateResult,
)
from app.models.research import CompanyResearchResult
from app.services.document_index_refresh import (
    DocumentIndexRefreshService,
)


class FakeDocumentIndexUpdateService:
    def __init__(
        self,
        result: DocumentIndexUpdateResult,
    ) -> None:
        self.result = result
        self.update_count = 0

    def update(
        self,
        research: CompanyResearchResult,
    ) -> DocumentIndexUpdateResult:
        del research

        self.update_count += 1
        return self.result


class FakeDocumentIndexSyncService:
    def __init__(self) -> None:
        self.sync_count = 0

    def sync(
        self,
        *,
        doc_id: str,
        version: str,
    ) -> DocumentIndexState:
        self.sync_count += 1

        return DocumentIndexState(
            doc_id=doc_id,
            version=version,
            indexed_at=datetime.now(UTC),
        )


def create_research() -> CompanyResearchResult:
    return CompanyResearchResult.model_construct(
        edinet_code="E02367",
    )


def test_refresh_performs_sync_when_required() -> None:
    update_service = FakeDocumentIndexUpdateService(
        DocumentIndexUpdateResult(
            doc_id="S100Y9NX",
            version="version-1",
            chunks_rebuilt=True,
            sync_required=True,
            chunk_count=6,
            reason="document_not_indexed",
        )
    )

    sync_service = FakeDocumentIndexSyncService()

    service = DocumentIndexRefreshService(
        update_service=update_service,
        sync_service=sync_service,
    )

    result = service.refresh(
        create_research()
    )

    assert update_service.update_count == 1
    assert sync_service.sync_count == 1

    assert result.chunks_rebuilt is True
    assert result.sync_performed is True
    assert result.chunk_count == 6
    assert result.reason == "document_not_indexed"
    assert result.indexed_at is not None


def test_refresh_syncs_pending_index_without_rebuilding() -> None:
    update_service = FakeDocumentIndexUpdateService(
        DocumentIndexUpdateResult(
            doc_id="S100Y9NX",
            version="version-1",
            chunks_rebuilt=False,
            sync_required=True,
            chunk_count=0,
            reason="index_sync_pending",
        )
    )

    sync_service = FakeDocumentIndexSyncService()

    service = DocumentIndexRefreshService(
        update_service=update_service,
        sync_service=sync_service,
    )

    result = service.refresh(
        create_research()
    )

    assert update_service.update_count == 1
    assert sync_service.sync_count == 1

    assert result.chunks_rebuilt is False
    assert result.sync_performed is True
    assert result.chunk_count == 0
    assert result.reason == "index_sync_pending"
    assert result.indexed_at is not None


def test_refresh_does_nothing_when_index_is_current() -> None:
    update_service = FakeDocumentIndexUpdateService(
        DocumentIndexUpdateResult(
            doc_id="S100Y9NX",
            version="version-1",
            chunks_rebuilt=False,
            sync_required=False,
            chunk_count=0,
            reason="document_unchanged",
        )
    )

    sync_service = FakeDocumentIndexSyncService()

    service = DocumentIndexRefreshService(
        update_service=update_service,
        sync_service=sync_service,
    )

    result = service.refresh(
        create_research()
    )

    assert update_service.update_count == 1
    assert sync_service.sync_count == 0

    assert result.chunks_rebuilt is False
    assert result.sync_performed is False
    assert result.chunk_count == 0
    assert result.reason == "document_unchanged"
    assert result.indexed_at is None