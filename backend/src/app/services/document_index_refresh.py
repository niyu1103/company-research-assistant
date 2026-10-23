from app.models.document_freshness import (
    DocumentIndexRefreshResult,
)
from app.models.research import CompanyResearchResult
from app.services.document_index_sync import (
    DocumentIndexSyncService,
)
from app.services.document_index_update import (
    DocumentIndexUpdateService,
)


class DocumentIndexRefreshService:
    def __init__(
        self,
        *,
        update_service: DocumentIndexUpdateService,
        sync_service: DocumentIndexSyncService,
    ) -> None:
        self.update_service = update_service
        self.sync_service = sync_service

    def refresh(
        self,
        research: CompanyResearchResult,
    ) -> DocumentIndexRefreshResult:
        update_result = self.update_service.update(research)

        if not update_result.sync_required:
            return DocumentIndexRefreshResult(
                doc_id=update_result.doc_id,
                edinet_code=research.edinet_code,
                version=update_result.version,
                chunks_rebuilt=(update_result.chunks_rebuilt),
                sync_performed=False,
                chunk_count=(update_result.chunk_count),
                reason=update_result.reason,
                indexed_at=update_result.indexed_at,
            )

        state = self.sync_service.sync(
            doc_id=update_result.doc_id,
            version=update_result.version,
        )

        return DocumentIndexRefreshResult(
            doc_id=update_result.doc_id,
            edinet_code=research.edinet_code,
            version=update_result.version,
            chunks_rebuilt=(update_result.chunks_rebuilt),
            sync_performed=True,
            chunk_count=(update_result.chunk_count),
            reason=update_result.reason,
            indexed_at=state.indexed_at,
        )
