from app.models.document_chunk import DocumentChunk
from app.repositories.document_chunk import DocumentChunkRepository
from app.services.document_chunking import DocumentChunkingService
from app.services.document_indexing import DocumentIndexingService


class FakeDocumentChunkRepository:
    def __init__(self) -> None:
        self.saved_doc_id: str | None = None
        self.saved_chunks: list[DocumentChunk] = []

    def create_table(self) -> None:
        pass

    def replace_for_document(
        self,
        doc_id: str,
        chunks: list[DocumentChunk],
    ) -> None:
        self.saved_doc_id = doc_id
        self.saved_chunks = chunks


def test_repository_matches_protocol() -> None:
    repository: DocumentChunkRepository = (
        FakeDocumentChunkRepository()
    )

    assert repository is not None


def test_index_company_research() -> None:
    # このテストでは CompanyResearchResult 全体を作る必要があるため、
    # 実際のモデルを使う統合テストは次の段階で追加する。
    repository = FakeDocumentChunkRepository()
    chunking_service = DocumentChunkingService()

    service = DocumentIndexingService(
        repository=repository,
        chunking_service=chunking_service,
    )

    assert service.repository is repository
    assert service.chunking_service is chunking_service