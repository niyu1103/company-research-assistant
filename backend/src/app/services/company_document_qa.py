from app.models.document_qa import (
    CompanyDocumentQAResult,
    CompanyDocumentQASource,
)
from app.services.company_research import (
    CompanyResearchService,
)
from app.services.document_answering import (
    DocumentAnsweringService,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.services.document_retrieval import (
    DocumentRetrievalService,
)


class CompanyDocumentQAService:
    def __init__(
        self,
        *,
        research_service: CompanyResearchService,
        query_planning_service: DocumentQueryPlanningService,
        retrieval_service: DocumentRetrievalService,
        answering_service: DocumentAnsweringService,
    ) -> None:
        self.research_service = research_service
        self.query_planning_service = query_planning_service
        self.retrieval_service = retrieval_service
        self.answering_service = answering_service

    async def answer(
        self,
        *,
        name: str,
        question: str,
    ) -> CompanyDocumentQAResult:
        research = await self.research_service.research(name=name)

        plan = await self.query_planning_service.plan(question)

        chunks = self.retrieval_service.retrieve(
            research=research,
            query_text=plan.query_text,
            num_results=3,
        )

        answer = await self.answering_service.answer(
            question=question,
            chunks=chunks,
        )

        return CompanyDocumentQAResult(
            name=name,
            question=question,
            query_text=plan.query_text,
            answer=answer.answer,
            evidence_chunk_ids=(answer.evidence_chunk_ids),
            insufficient_context=(answer.insufficient_context),
            sources=[
                CompanyDocumentQASource(
                    chunk_id=chunk.chunk_id,
                    section=chunk.section,
                    score=chunk.score,
                )
                for chunk in chunks
                if chunk.chunk_id in answer.evidence_chunk_ids
            ],
        )
