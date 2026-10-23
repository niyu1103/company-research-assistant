from datetime import UTC, datetime

from app.services.document_freshness import (
    DocumentFreshnessService,
)


def test_new_document_should_rebuild_and_sync() -> None:
    service = DocumentFreshnessService()

    result = service.decide(
        previous_version=None,
        current_version="version-1",
        indexed_at=None,
    )

    assert result.should_rebuild_chunks is True
    assert result.should_sync_index is True
    assert result.reason == "document_not_indexed"


def test_changed_document_should_rebuild_and_sync() -> None:
    service = DocumentFreshnessService()

    result = service.decide(
        previous_version="version-1",
        current_version="version-2",
        indexed_at=datetime.now(UTC),
    )

    assert result.should_rebuild_chunks is True
    assert result.should_sync_index is True
    assert result.reason == "document_changed"


def test_unchanged_synced_document_should_do_nothing() -> None:
    service = DocumentFreshnessService()

    result = service.decide(
        previous_version="version-1",
        current_version="version-1",
        indexed_at=datetime.now(UTC),
    )

    assert result.should_rebuild_chunks is False
    assert result.should_sync_index is False
    assert result.reason == "document_unchanged"


def test_unchanged_document_with_pending_sync_should_sync() -> None:
    service = DocumentFreshnessService()

    result = service.decide(
        previous_version="version-1",
        current_version="version-1",
        indexed_at=None,
    )

    assert result.should_rebuild_chunks is False
    assert result.should_sync_index is True
    assert result.reason == "index_sync_pending"