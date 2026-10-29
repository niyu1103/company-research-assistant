import pytest

from app.models.document_answer import DocumentAnswer
from app.models.document_chunk import RetrievedDocumentChunk
from app.models.document_query import DocumentQueryPlan
from app.models.edinet import EdinetDocument
from app.models.research import CompanyResearchResult
from app.services.company_document_qa import (
    CompanyDocumentQAService,
)
from app.models.company_fact import CompanyFactAnswer
from app.models.company_question_route import (
    CompanyQuestionRoute,
)
from app.clients.edinet import EdinetClient
from app.services.company_financial import (
    CompanyFinancialService,
)
from app.services.financial_question_planner import (
    FinancialQuestionPlannerService,
)
from app.models.company_question_route import CompanyQuestionRoute
from app.models.financial import (
    FinancialHistory,
    FinancialYearValue,
)
from app.models.financial_question import (
    FinancialQuestionPlan,
)
from app.models.company import CompanyDetail

from app.services.company_analysis import (
    CompanyAnalysisService,
)
from app.services.company_analysis_question import (
    CompanyAnalysisQuestionService,
)
from app.models.company_analysis_question import (
    CompanyAnalysisQuestionAnswer,
)
from app.models.financial import (
    FinancialHistory,
    FinancialYearValue,
)
from app.models.financial import FinancialTrend

class FakeCompanyResearchService:
    async def research(
        self,
        *,
        name: str,
    ) -> CompanyResearchResult:
        return CompanyResearchResult.model_construct(
            company=CompanyDetail.model_construct(
                name="テスト株式会社",
            ),
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


class FakeCompanyQuestionRouterService:
    async def route(
        self,
        question: str,
    ) -> CompanyQuestionRoute:
        del question

        return CompanyQuestionRoute(
            route="document",
            reason="test",
        )


class FakeCompanyFactsService:
    def answer(
        self,
        *,
        research,
        question: str,
    ) -> CompanyFactAnswer:
        del research
        del question

        return CompanyFactAnswer(
            fact_key=None,
            answer="",
            insufficient_context=True,
        )

class FakeCompanyFactsRouterService:
    async def route(
        self,
        question: str,
    ) -> CompanyQuestionRoute:
        del question

        return CompanyQuestionRoute(
            route="company_facts",
            reason="test",
        )


class FakeCompanyFactsAnswerService:
    def answer(
        self,
        *,
        research,
        question: str,
    ) -> CompanyFactAnswer:
        del research
        del question

        return CompanyFactAnswer(
            fact_key="employee_number",
            answer="トヨタ自動車株式会社の従業員数は1000人です。",
            insufficient_context=False,
        )

class FakeFinancialRouterService:
    async def route(
        self,
        question: str,
    ) -> CompanyQuestionRoute:
        return CompanyQuestionRoute(
            route="financial",
            reason="財務情報についての質問",
        )


class FakeFinancialQuestionPlannerService(
    FinancialQuestionPlannerService
):
    async def plan(
        self,
        question: str,
    ) -> FinancialQuestionPlan:
        return FinancialQuestionPlan(
            metric="revenue",
            operation="max",
            years=5,
        )


class FakeEdinetClient(EdinetClient):
    async def get_financial_history(
        self,
        doc_id: str,
    ) -> FinancialHistory:
        return FinancialHistory.model_construct(
            revenue=[
                FinancialYearValue.model_construct(
                    value=100_000_000,
                    context_id="Prior4YearDuration",
                    relative_year="四期前",
                ),
                FinancialYearValue.model_construct(
                    value=300_000_000,
                    context_id="Prior3YearDuration",
                    relative_year="三期前",
                ),
                FinancialYearValue.model_construct(
                    value=200_000_000,
                    context_id="Prior2YearDuration",
                    relative_year="前々期",
                ),
                FinancialYearValue.model_construct(
                    value=250_000_000,
                    context_id="Prior1YearDuration",
                    relative_year="前期",
                ),
                FinancialYearValue.model_construct(
                    value=280_000_000,
                    context_id="CurrentYearDuration",
                    relative_year="当期",
                ),
            ],
            operating_income=[],
            net_income=[],
            total_assets=[],
            operating_cash_flow=[],
        )
class FakeAnalysisRouterService:
    async def route(
        self,
        question: str,
    ) -> CompanyQuestionRoute:
        return CompanyQuestionRoute(
            route="analysis",
            reason="複数の情報を統合して分析する質問",
        )


class FakeAnalysisEdinetClient(EdinetClient):
    async def get_financial_history(
        self,
        doc_id: str,
    ) -> FinancialHistory:
        return FinancialHistory.model_construct(
            revenue=[
                FinancialYearValue.model_construct(
                    value=100_000_000,
                    context_id="Prior1YearDuration",
                    relative_year="前期",
                ),
                FinancialYearValue.model_construct(
                    value=120_000_000,
                    context_id="CurrentYearDuration",
                    relative_year="当期",
                ),
            ],
            operating_income=[],
            profit_before_tax=[],
            net_income=[],
            total_assets=[],
            operating_cash_flow=[],
        )


class FakeCompanyAnalysisQuestionService(
    CompanyAnalysisQuestionService
):
    async def answer(
        self,
        *,
        question: str,
        research: CompanyResearchResult,
        financial_trend: FinancialTrend,
        chunks: list[RetrievedDocumentChunk],
    ) -> CompanyAnalysisQuestionAnswer:
        return CompanyAnalysisQuestionAnswer(
            answer=(
                "売上は増加傾向ですが、"
                "事業リスクもあるため、"
                "今後の成長は断定できません。"
            ),
            evidence_chunk_ids=[
                chunks[0].chunk_id
            ],
            insufficient_context=False,
        )

class FakeDocumentIndexRefreshService:
    def __init__(self) -> None:
        self.call_count = 0

    def refresh(
        self,
        research: CompanyResearchResult,
    ) -> None:
        del research
        self.call_count += 1



class FakeDocumentContextSufficiencyService:
    def __init__(
        self,
        sufficient: bool = True,
    ) -> None:
        self.sufficient = sufficient
        self.call_count = 0

    async def is_sufficient(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> bool:
        del question, chunks

        self.call_count += 1

        return self.sufficient


class FailingDocumentAnsweringService:
    async def answer(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> DocumentAnswer:
        del question, chunks

        raise AssertionError(
            "AnsweringService must not be called "
            "when context is insufficient"
        )

class FailingDocumentRetrievalService:
    def retrieve(
        self,
        *,
        research,
        query_text: str,
        num_results: int,
    ):
        del research
        del query_text
        del num_results

        raise AssertionError(
            "Retrieval should not be called for company_facts"
        )
class FailingDocumentAnsweringService(
    FakeDocumentAnsweringService
):
    async def answer(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ):
        raise AssertionError(
            "analysis route must not use DocumentAnsweringService"
        )



@pytest.mark.anyio
async def test_company_document_qa_service() -> None:
    retrieval_service = (
        FakeDocumentRetrievalService()
    )
    
    refresh_service = FakeDocumentIndexRefreshService()

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
        question_router_service=(
            FakeCompanyQuestionRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsService()
        ),
        financial_question_planner_service=(
            FinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=EdinetClient(),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            CompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService()
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
    
    assert refresh_service.call_count == 1


@pytest.mark.anyio
async def test_company_document_qa_service_insufficient_context() -> None:
    refresh_service = FakeDocumentIndexRefreshService()
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
        question_router_service=(
            FakeCompanyQuestionRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsService()
        ),
        financial_question_planner_service=(
            FinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=EdinetClient(),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            CompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService()
        ),
    )

    result = await service.answer(
        name="任天堂",
        question="社員食堂の人気メニューは？",
    )

    assert result.insufficient_context is True
    assert result.evidence_chunk_ids == []
    assert result.sources == []
    assert refresh_service.call_count == 1

@pytest.mark.anyio
async def test_company_facts_does_not_use_rag() -> None:
    refresh_service = FakeDocumentIndexRefreshService()
    service = CompanyDocumentQAService(
        research_service=(
            FakeCompanyResearchService()
        ),
        query_planning_service=(
            FakeDocumentQueryPlanningService()
        ),
        retrieval_service=(
            FailingDocumentRetrievalService()
        ),
        answering_service=(
            FakeDocumentAnsweringService()
        ),
        question_router_service=(
            FakeCompanyFactsRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsAnswerService()
        ),
        financial_question_planner_service=(
            FinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=EdinetClient(),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            CompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService()
        ),
    )

    result = await service.answer(
        name="トヨタ自動車",
        question="従業員は何人？",
    )

    assert result.query_text == "company_facts"
    assert result.answer == (
        "トヨタ自動車株式会社の従業員数は1000人です。"
    )
    assert result.insufficient_context is False
    assert result.evidence_chunk_ids == []
    assert result.sources == []
    assert refresh_service.call_count == 0

@pytest.mark.anyio
async def test_financial_does_not_use_rag() -> None:
    refresh_service = FakeDocumentIndexRefreshService()
    service = CompanyDocumentQAService(
        research_service=(
            FakeCompanyResearchService()
        ),
        query_planning_service=(
            FakeDocumentQueryPlanningService()
        ),
        retrieval_service=(
            FailingDocumentRetrievalService()
        ),
        answering_service=(
            FakeDocumentAnsweringService()
        ),
        question_router_service=(
            FakeFinancialRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsService()
        ),
        financial_question_planner_service=(
            FakeFinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=FakeEdinetClient(),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            CompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService()
        ),
    )

    result = await service.answer(
        name="テスト株式会社",
        question="過去5期で一番売上が高かったのは？",
    )

    assert result.query_text == "financial"
    assert result.insufficient_context is False
    assert result.evidence_chunk_ids == []
    assert result.sources == []
    assert refresh_service.call_count == 0

    assert "売上高" in result.answer
    assert "3億円" in result.answer

@pytest.mark.anyio
async def test_analysis_does_not_use_document_answerer() -> None:
    refresh_service = FakeDocumentIndexRefreshService()
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
            FailingDocumentAnsweringService()
        ),
        question_router_service=(
            FakeAnalysisRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsService()
        ),
        financial_question_planner_service=(
            FinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=(
            FakeAnalysisEdinetClient()
        ),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            FakeCompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService()
        ),
    )

    result = await service.answer(
        name="テスト株式会社",
        question="今後成長しそう？",
    )

    assert result.insufficient_context is False
    assert result.answer == (
        "売上は増加傾向ですが、"
        "事業リスクもあるため、"
        "今後の成長は断定できません。"
    )
    assert refresh_service.call_count == 1
    assert len(result.evidence_chunk_ids) == 1
    assert len(result.sources) == 1



@pytest.mark.anyio
async def test_document_insufficient_context_stops_before_answering() -> None:
    refresh_service = FakeDocumentIndexRefreshService()

    service = CompanyDocumentQAService(
        research_service=FakeCompanyResearchService(),
        query_planning_service=(
            FakeDocumentQueryPlanningService()
        ),
        retrieval_service=(
            FakeDocumentRetrievalService()
        ),
        answering_service=(
            FailingDocumentAnsweringService()
        ),
        question_router_service=(
            FakeCompanyQuestionRouterService()
        ),
        company_facts_service=(
            FakeCompanyFactsService()
        ),
        financial_question_planner_service=(
            FinancialQuestionPlannerService()
        ),
        company_financial_service=(
            CompanyFinancialService()
        ),
        edinet_client=EdinetClient(),
        company_analysis_service=(
            CompanyAnalysisService()
        ),
        company_analysis_question_service=(
            CompanyAnalysisQuestionService()
        ),
        document_index_refresh_service=refresh_service,
        context_sufficiency_service=(
            FakeDocumentContextSufficiencyService(
                sufficient=False
            )
        ),
    )

    result = await service.answer(
        name="任天堂",
        question="社風は？",
    )

    assert result.insufficient_context is True
    assert result.evidence_chunk_ids == []
    assert result.sources == []
    assert refresh_service.call_count == 1