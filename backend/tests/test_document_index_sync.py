import pytest

from app.models.document_freshness import (
    DocumentIndexState,
)
from app.services.document_index_sync import (
    DocumentIndexSyncService,
)


class FakeDocumentIndexSyncRepository:
    def __init__(
        self,
        *,
        should_fail: bool = False,
    ) -> None:
        self.should_fail = should_fail
        self.sync_count = 0

    def sync_and_wait(self) -> None:
        self.sync_count += 1

        if self.should_fail:
            raise RuntimeError(
                "AI Search sync failed"
            )


class FakeDocumentIndexStateRepository:
    def __init__(self) -> None:
        self.saved_states: list[
            DocumentIndexState
        ] = []

    def find_by_doc_id(
        self,
        doc_id: str,
    ) -> DocumentIndexState | None:
        del doc_id
        return None

    def save(
        self,
        state: DocumentIndexState,
    ) -> None:
        self.saved_states.append(
            state
        )


def test_successful_sync_saves_indexed_at() -> None:
    sync_repository = (
        FakeDocumentIndexSyncRepository()
    )
    state_repository = (
        FakeDocumentIndexStateRepository()
    )

    service = DocumentIndexSyncService(
        sync_repository=sync_repository,
        state_repository=state_repository,
    )

    result = service.sync(
        doc_id="S100Y9NX",
        version="version-1",
    )

    assert sync_repository.sync_count == 1

    assert len(
        state_repository.saved_states
    ) == 1

    saved_state = (
        state_repository.saved_states[0]
    )

    assert saved_state.doc_id == "S100Y9NX"
    assert saved_state.version == "version-1"
    assert saved_state.indexed_at is not None

    assert result == saved_state


def test_failed_sync_does_not_save_indexed_at() -> None:
    sync_repository = (
        FakeDocumentIndexSyncRepository(
            should_fail=True,
        )
    )
    state_repository = (
        FakeDocumentIndexStateRepository()
    )

    service = DocumentIndexSyncService(
        sync_repository=sync_repository,
        state_repository=state_repository,
    )

    with pytest.raises(
        RuntimeError,
        match="AI Search sync failed",
    ):
        service.sync(
            doc_id="S100Y9NX",
            version="version-1",
        )

    assert sync_repository.sync_count == 1

    assert (
        state_repository.saved_states
        == []
    )