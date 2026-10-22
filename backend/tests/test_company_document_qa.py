import pytest

from app.models.document_answer import DocumentAnswer
from app.models.document_chunk import RetrievedDocumentChunk
from app.models.document_query import DocumentQueryPlan
from app.models.edinet import EdinetDocument
from app.models.research import CompanyResearchResult
from app.services.company_document_qa import (
    CompanyDocumentQAService,
)


class FakeCompanyResearchService:
    async def research(
        self,
        *,
        name: str,
    ) -> CompanyResearchResult:
        return CompanyResearchResult.model_construct(
            edinet_code="E02367",
            annual_report=EdinetDocument.model_construct(
                doc_id="S100Y9NX",
            ),
        )


class FakeDocumentQueryPlanningService:
    async def plan(
        self,
        question: str,
    ) -> DocumentQueryPlan:
        return DocumentQueryPlan(
            query_text="サイバー攻撃",
        )


class FakeDocumentRetrievalService:
    def __init__(self) -> None:
        self.received_query_text: str | None = None
        self.received_edinet_code: str | None = None
        self.received_doc_id: str | None = None

    def retrieve(
        self,
        *,
        research: CompanyResearchResult,
        query_text: str,
        num_results: int = 5,
    ) -> list[RetrievedDocumentChunk]:
        self.received_query_text = query_text
        self.received_edinet_code = research.edinet_code
        self.received_doc_id = research.annual_report.doc_id

        return [
            RetrievedDocumentChunk(
                chunk_id="S100Y9NX_business_risks_2",
                doc_id="S100Y9NX",
                edinet_code="E02367",
                section="business_risks",
                chunk_index=2,
                content="サイバー攻撃に関する記載",
                score=1.0,
            ),
            RetrievedDocumentChunk(
                chunk_id="S100Y9NX_business_risks_3",
                doc_id="S100Y9NX",
                edinet_code="E02367",
                section="business_risks",
                chunk_index=3,
                content="不正アクセスに関する記載",
                score=0.9,
            ),
        ]


class FakeDocumentAnsweringService:
    async def answer(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> DocumentAnswer:
        del question, chunks
        return DocumentAnswer(
            answer="サイバー攻撃によるリスクがあります。",
            evidence_chunk_ids=[
                "S100Y9NX_business_risks_2",
            ],
            insufficient_context=False,
        )

class FakeInsufficientDocumentAnsweringService:
    async def answer(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> DocumentAnswer:
        del question, chunks
        return DocumentAnswer(
            answer="資料には記載されていません。",
            evidence_chunk_ids=[],
            insufficient_context=True,
        )


@pytest.mark.anyio
async def test_company_document_qa_service() -> None:
    retrieval_service = (
        FakeDocumentRetrievalService()
    )

    service = CompanyDocumentQAService(
        research_service=(
            FakeCompanyResearchService()
        ),
        query_planning_service=(
            FakeDocumentQueryPlanningService()
        ),
        retrieval_service=retrieval_service,
        answering_service=(
            FakeDocumentAnsweringService()
        ),
    )

    result = await service.answer(
        name="任天堂",
        question="サイバー攻撃のリスクは？",
    )

    assert result.name == "任天堂"
    assert result.query_text == "サイバー攻撃"

    assert (
        retrieval_service.received_query_text
        == "サイバー攻撃"
    )
    assert (
        retrieval_service.received_edinet_code
        == "E02367"
    )
    assert (
        retrieval_service.received_doc_id
        == "S100Y9NX"
    )

    assert result.evidence_chunk_ids == [
        "S100Y9NX_business_risks_2"
    ]

    assert len(result.sources) == 1

    assert (
        result.sources[0].chunk_id
        == "S100Y9NX_business_risks_2"
    )

    assert (
        result.sources[0].section
        == "business_risks"
    )

    assert result.insufficient_context is False

@pytest.mark.anyio
async def test_company_document_qa_service_insufficient_context() -> None:
    service = CompanyDocumentQAService(
        research_service=(
            FakeCompanyResearchService()
        ),
        query_planning_service=(
            FakeDocumentQueryPlanningService()
        ),
        retrieval_service=(
            FakeDocumentRetrievalService()
        ),
        answering_service=(
            FakeInsufficientDocumentAnsweringService()
        ),
    )

    result = await service.answer(
        name="任天堂",
        question="社員食堂の人気メニューは？",
    )

    assert result.insufficient_context is True
    assert result.evidence_chunk_ids == []
    assert result.sources == []