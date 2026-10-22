from app.models.document_chunk import RetrievedDocumentChunk
from app.repositories.document_search import DocumentSearchRepository
from app.services.document_retrieval import DocumentRetrievalService


class FakeDocumentSearchRepository:
    def __init__(self) -> None:
        self.query_text: str | None = None
        self.edinet_code: str | None = None
        self.doc_id: str | None = None
        self.num_results: int | None = None

    def search(
        self,
        *,
        query_text: str,
        edinet_code: str,
        doc_id: str,
        num_results: int = 5,
    ) -> list[RetrievedDocumentChunk]:
        self.query_text = query_text
        self.edinet_code = edinet_code
        self.doc_id = doc_id
        self.num_results = num_results

        return []


def test_repository_matches_protocol() -> None:
    repository: DocumentSearchRepository = (
        FakeDocumentSearchRepository()
    )

    assert repository is not None


def test_retrieve_returns_empty_for_blank_query() -> None:
    repository = FakeDocumentSearchRepository()

    service = DocumentRetrievalService(
        repository=repository,
    )

    # researchを必要としないよう、
    # blank queryならrepository呼び出し前に終了することを確認
    result = service.retrieve(
        research=None,  # type: ignore[arg-type]
        query_text="   ",
    )

    assert result == []
    assert repository.query_text is None