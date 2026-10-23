from datetime import UTC, datetime

from app.models.document_chunk import DocumentChunk
from app.models.document_freshness import DocumentIndexState
from app.models.edinet import (
    EdinetDocument,
    EdinetNarrativeSummary,
)
from app.models.research import CompanyResearchResult
from app.services.document_chunking import (
    DocumentChunkingService,
)
from app.services.document_freshness import (
    DocumentFreshnessService,
)
from app.services.document_index_update import (
    DocumentIndexUpdateService,
)
from app.services.document_indexing import (
    DocumentIndexingService,
)
from app.services.document_versioning import (
    DocumentVersioningService,
)


class FakeDocumentChunkRepository:
    def __init__(self) -> None:
        self.replace_count = 0
        self.saved_chunks: list[DocumentChunk] = []

    def replace_for_document(
        self,
        *,
        doc_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        del doc_id

        self.replace_count += 1
        self.saved_chunks = chunks


class FakeDocumentIndexStateRepository:
    def __init__(
        self,
        state: DocumentIndexState | None = None,
    ) -> None:
        self.state = state
        self.save_count = 0

    def find_by_doc_id(
        self,
        doc_id: str,
    ) -> DocumentIndexState | None:
        del doc_id
        return self.state

    def save(
        self,
        state: DocumentIndexState,
    ) -> None:
        self.save_count += 1
        self.state = state


def create_research() -> CompanyResearchResult:
    return CompanyResearchResult.model_construct(
        edinet_code="E02367",
        annual_report=EdinetDocument.model_construct(
            doc_id="S100Y9NX",
        ),
        narratives=EdinetNarrativeSummary(
            business_overview=(
                "ホームエンターテインメント分野で"
                "娯楽製品を開発・製造・販売しています。"
            ),
            business_risks=(
                "サイバー攻撃によりシステム停止や"
                "情報漏えいが発生する可能性があります。"
            ),
        ),
    )


def create_service(
    *,
    state_repository: FakeDocumentIndexStateRepository,
    chunk_repository: FakeDocumentChunkRepository,
) -> DocumentIndexUpdateService:
    indexing_service = DocumentIndexingService(
        repository=chunk_repository,
        chunking_service=DocumentChunkingService(),
    )

    return DocumentIndexUpdateService(
        indexing_service=indexing_service,
        versioning_service=DocumentVersioningService(),
        freshness_service=DocumentFreshnessService(),
        state_repository=state_repository,
    )


def create_version(
    research: CompanyResearchResult,
) -> str:
    return DocumentVersioningService().create_version(
        doc_id=research.annual_report.doc_id,
        business_overview=(
            research.narratives.business_overview
        ),
        business_risks=(
            research.narratives.business_risks
        ),
    )


def test_new_document_rebuilds_chunks_and_requires_sync() -> None:
    research = create_research()

    chunk_repository = FakeDocumentChunkRepository()
    state_repository = FakeDocumentIndexStateRepository()

    service = create_service(
        state_repository=state_repository,
        chunk_repository=chunk_repository,
    )

    result = service.update(research)

    assert result.chunks_rebuilt is True
    assert result.sync_required is True
    assert result.chunk_count > 0
    assert result.reason == "document_not_indexed"
    assert result.indexed_at is None

    assert chunk_repository.replace_count == 1
    assert state_repository.save_count == 1
    assert state_repository.state is not None
    assert state_repository.state.indexed_at is None


def test_changed_document_rebuilds_chunks_and_requires_sync() -> None:
    research = create_research()

    chunk_repository = FakeDocumentChunkRepository()

    previous_indexed_at = datetime.now(UTC)

    state_repository = FakeDocumentIndexStateRepository(
        DocumentIndexState(
            doc_id="S100Y9NX",
            version="old-version",
            indexed_at=previous_indexed_at,
        )
    )

    service = create_service(
        state_repository=state_repository,
        chunk_repository=chunk_repository,
    )

    result = service.update(research)

    assert result.chunks_rebuilt is True
    assert result.sync_required is True
    assert result.chunk_count > 0
    assert result.reason == "document_changed"
    assert result.indexed_at is None

    assert chunk_repository.replace_count == 1
    assert state_repository.save_count == 1
    assert state_repository.state is not None
    assert state_repository.state.version != "old-version"
    assert state_repository.state.indexed_at is None


def test_unchanged_synced_document_does_nothing() -> None:
    research = create_research()
    version = create_version(research)

    chunk_repository = FakeDocumentChunkRepository()

    indexed_at = datetime.now(UTC)

    state_repository = FakeDocumentIndexStateRepository(
        DocumentIndexState(
            doc_id="S100Y9NX",
            version=version,
            indexed_at=indexed_at,
        )
    )

    service = create_service(
        state_repository=state_repository,
        chunk_repository=chunk_repository,
    )

    result = service.update(research)

    assert result.chunks_rebuilt is False
    assert result.sync_required is False
    assert result.chunk_count == 0
    assert result.reason == "document_unchanged"
    assert result.indexed_at == indexed_at

    assert chunk_repository.replace_count == 0
    assert state_repository.save_count == 0


def test_unchanged_pending_document_requires_sync_only() -> None:
    research = create_research()
    version = create_version(research)

    chunk_repository = FakeDocumentChunkRepository()

    state_repository = FakeDocumentIndexStateRepository(
        DocumentIndexState(
            doc_id="S100Y9NX",
            version=version,
            indexed_at=None,
        )
    )

    service = create_service(
        state_repository=state_repository,
        chunk_repository=chunk_repository,
    )

    result = service.update(research)

    assert result.chunks_rebuilt is False
    assert result.sync_required is True
    assert result.chunk_count == 0
    assert result.reason == "index_sync_pending"
    assert result.indexed_at is None

    assert chunk_repository.replace_count == 0
    assert state_repository.save_count == 0