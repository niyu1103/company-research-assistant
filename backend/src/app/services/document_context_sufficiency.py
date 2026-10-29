from app.models.document_chunk import (
    RetrievedDocumentChunk,
)
from app.services.context_sufficiency_evaluation import (
    ContextSufficiencyEvaluationService,
)


class DocumentContextSufficiencyService:
    def __init__(self) -> None:
        self.evaluation_service = ContextSufficiencyEvaluationService()

    async def is_sufficient(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> bool:
        result = await self.evaluation_service.evaluate(
            question=question,
            chunks=chunks,
        )

        return result.sufficient
