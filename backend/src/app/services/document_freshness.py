from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DocumentFreshnessDecision:
    should_rebuild_chunks: bool
    should_sync_index: bool
    reason: str


class DocumentFreshnessService:
    def decide(
        self,
        *,
        previous_version: str | None,
        current_version: str,
        indexed_at: datetime | None,
    ) -> DocumentFreshnessDecision:
        if previous_version is None:
            return DocumentFreshnessDecision(
                should_rebuild_chunks=True,
                should_sync_index=True,
                reason="document_not_indexed",
            )

        if previous_version != current_version:
            return DocumentFreshnessDecision(
                should_rebuild_chunks=True,
                should_sync_index=True,
                reason="document_changed",
            )

        if indexed_at is None:
            return DocumentFreshnessDecision(
                should_rebuild_chunks=False,
                should_sync_index=True,
                reason="index_sync_pending",
            )

        return DocumentFreshnessDecision(
            should_rebuild_chunks=False,
            should_sync_index=False,
            reason="document_unchanged",
        )
