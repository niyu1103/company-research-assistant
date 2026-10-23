from app.models.document_freshness import (
    DocumentIndexState,
    DocumentIndexUpdateResult,
)
from app.models.research import CompanyResearchResult
from app.repositories.document_index_state import (
    DocumentIndexStateRepository,
)
from app.services.document_freshness import (
    DocumentFreshnessService,
)
from app.services.document_indexing import (
    DocumentIndexingService,
)
from app.services.document_versioning import (
    DocumentVersioningService,
)


class DocumentIndexUpdateService:
    def __init__(
        self,
        *,
        indexing_service: DocumentIndexingService,
        versioning_service: DocumentVersioningService,
        freshness_service: DocumentFreshnessService,
        state_repository: DocumentIndexStateRepository,
    ) -> None:
        self.indexing_service = indexing_service
        self.versioning_service = versioning_service
        self.freshness_service = freshness_service
        self.state_repository = state_repository

    def update(
        self,
        research: CompanyResearchResult,
    ) -> DocumentIndexUpdateResult:
        doc_id = research.annual_report.doc_id

        version = self.versioning_service.create_version(
            doc_id=doc_id,
            business_overview=(research.narratives.business_overview),
            business_risks=(research.narratives.business_risks),
        )

        previous_state = self.state_repository.find_by_doc_id(doc_id)

        previous_version = (
            previous_state.version if previous_state is not None else None
        )

        indexed_at = previous_state.indexed_at if previous_state is not None else None

        decision = self.freshness_service.decide(
            previous_version=previous_version,
            current_version=version,
            indexed_at=indexed_at,
        )

        if not decision.should_rebuild_chunks:
            return DocumentIndexUpdateResult(
                doc_id=doc_id,
                version=version,
                chunks_rebuilt=False,
                sync_required=decision.should_sync_index,
                chunk_count=0,
                reason=decision.reason,
                indexed_at=indexed_at,
            )

        if not decision.should_rebuild_chunks:
            return DocumentIndexUpdateResult(
                doc_id=doc_id,
                version=version,
                chunks_rebuilt=False,
                sync_required=(decision.should_sync_index),
                chunk_count=0,
                reason=decision.reason,
                indexed_at=indexed_at,
            )

        chunks = self.indexing_service.index_company_research(research)

        self.state_repository.save(
            DocumentIndexState(
                doc_id=doc_id,
                version=version,
                indexed_at=None,
            )
        )

        return DocumentIndexUpdateResult(
            doc_id=doc_id,
            version=version,
            chunks_rebuilt=True,
            sync_required=(decision.should_sync_index),
            chunk_count=len(chunks),
            reason=decision.reason,
            indexed_at=None,
        )
