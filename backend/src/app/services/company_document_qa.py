from anyio import to_thread

from app.clients.edinet import EdinetClient
from app.models.document_qa import (
    CompanyDocumentQAResult,
    CompanyDocumentQASource,
)
from app.models.financial import FinancialYearValue
from app.services.company_analysis import (
    CompanyAnalysisService,
)
from app.services.company_analysis_question import (
    CompanyAnalysisQuestionService,
)
from app.services.company_facts import CompanyFactsService
from app.services.company_financial import CompanyFinancialService
from app.services.company_question_router import (
    CompanyQuestionRouterService,
)
from app.services.company_research import (
    CompanyResearchService,
)
from app.services.document_answering import (
    DocumentAnsweringService,
)
from app.services.document_context_sufficiency import (
    DocumentContextSufficiencyService,
)
from app.services.document_index_refresh import (
    DocumentIndexRefreshService,
)
from app.services.document_query_planning import (
    DocumentQueryPlanningService,
)
from app.services.document_retrieval import (
    DocumentRetrievalService,
)
from app.services.financial_question_planner import (
    FinancialQuestionPlannerService,
)


class CompanyDocumentQAService:
    def __init__(
        self,
        *,
        research_service: CompanyResearchService,
        query_planning_service: DocumentQueryPlanningService,
        retrieval_service: DocumentRetrievalService,
        answering_service: DocumentAnsweringService,
        question_router_service: CompanyQuestionRouterService,
        company_facts_service: CompanyFactsService,
        financial_question_planner_service: FinancialQuestionPlannerService,
        company_financial_service: CompanyFinancialService,
        edinet_client: EdinetClient,
        company_analysis_service: CompanyAnalysisService,
        company_analysis_question_service: CompanyAnalysisQuestionService,
        document_index_refresh_service: DocumentIndexRefreshService,
        context_sufficiency_service: DocumentContextSufficiencyService,
    ) -> None:
        self.research_service = research_service
        self.query_planning_service = query_planning_service
        self.retrieval_service = retrieval_service
        self.answering_service = answering_service
        self.question_router_service = question_router_service
        self.company_facts_service = company_facts_service
        self.financial_question_planner_service = financial_question_planner_service
        self.company_financial_service = company_financial_service
        self.edinet_client = edinet_client
        self.company_analysis_service = company_analysis_service
        self.company_analysis_question_service = company_analysis_question_service
        self.document_index_refresh_service = document_index_refresh_service
        self.context_sufficiency_service = context_sufficiency_service

    async def answer(
        self,
        *,
        name: str,
        question: str,
    ) -> CompanyDocumentQAResult:
        research = await self.research_service.research(
            name=name,
        )

        route = await self.question_router_service.route(question)

        if route.route == "company_facts":
            fact_answer = self.company_facts_service.answer(
                research=research,
                question=question,
            )

            return CompanyDocumentQAResult(
                name=name,
                question=question,
                query_text="company_facts",
                answer=fact_answer.answer,
                evidence_chunk_ids=[],
                insufficient_context=(fact_answer.insufficient_context),
                sources=[],
            )

        if route.route == "financial":
            financial_plan = await self.financial_question_planner_service.plan(
                question
            )

            if (
                financial_plan.requires_specific_period
                and not financial_plan.specific_years
            ):
                period = financial_plan.period_hint or "指定された期間"

                return CompanyDocumentQAResult(
                    name=research.company.name,
                    question=question,
                    query_text="financial",
                    answer=(
                        f"{period}について比較するには、"
                        "対象期間の複数年度の財務データが必要です。"
                        "現在取得している財務データだけでは、"
                        "正確に判断できません。"
                    ),
                    evidence_chunk_ids=[],
                    insufficient_context=True,
                    sources=[],
                )

            financial_history = await self.edinet_client.get_financial_history(
                research.annual_report.doc_id
            )

            specific_year_values: dict[
                int,
                FinancialYearValue,
            ] = {}

            if financial_plan.specific_years:
                missing_years = (
                    self.company_financial_service.find_missing_specific_years(
                        research=research,
                        history=financial_history,
                        plan=financial_plan,
                    )
                )

                if missing_years:
                    unresolved_years: list[int] = []

                    if financial_plan.metric is None:
                        unresolved_years.extend(missing_years)
                    else:
                        for year in missing_years:
                            doc_id = await self.research_service.find_annual_report_doc_id_by_period_end_year(
                                edinet_code=(research.edinet_code),
                                year=year,
                            )

                            if doc_id is None:
                                unresolved_years.append(year)
                                continue

                            historical_history = (
                                await self.edinet_client.get_financial_history(doc_id)
                            )

                            current_value = self.company_financial_service.find_current_metric_value(
                                history=(historical_history),
                                metric=(financial_plan.metric),
                            )

                            if current_value is None:
                                unresolved_years.append(year)
                                continue

                            specific_year_values[year] = current_value

                    if unresolved_years:
                        missing_year_text = "、".join(
                            f"{year}年" for year in unresolved_years
                        )

                        return CompanyDocumentQAResult(
                            name=research.company.name,
                            question=question,
                            query_text="financial",
                            answer=(
                                f"{missing_year_text}の"
                                "財務データを"
                                "取得できませんでした。"
                            ),
                            evidence_chunk_ids=[],
                            insufficient_context=True,
                            sources=[],
                        )

            financial_answer = self.company_financial_service.answer(
                research=research,
                history=financial_history,
                plan=financial_plan,
                specific_year_values=(specific_year_values),
            )

            return CompanyDocumentQAResult(
                name=name,
                question=question,
                query_text="financial",
                answer=financial_answer.answer,
                evidence_chunk_ids=[],
                insufficient_context=(financial_answer.insufficient_context),
                sources=[],
            )

        if route.route in {"document", "analysis"}:
            await to_thread.run_sync(
                self.document_index_refresh_service.refresh,
                research,
            )

        if route.route == "analysis":
            financial_history = await self.edinet_client.get_financial_history(
                research.annual_report.doc_id
            )

            financial_trend = self.company_analysis_service.build_financial_trend(
                financial_history
            )

            plan = await self.query_planning_service.plan(question)

            chunks = self.retrieval_service.retrieve(
                research=research,
                query_text=plan.query_text,
                num_results=5,
            )

            analysis_answer = await self.company_analysis_question_service.answer(
                question=question,
                research=research,
                financial_trend=financial_trend,
                chunks=chunks,
            )

            return CompanyDocumentQAResult(
                name=name,
                question=question,
                query_text=plan.query_text,
                answer=analysis_answer.answer,
                evidence_chunk_ids=(analysis_answer.evidence_chunk_ids),
                insufficient_context=(analysis_answer.insufficient_context),
                sources=[
                    CompanyDocumentQASource(
                        chunk_id=chunk.chunk_id,
                        section=chunk.section,
                        score=chunk.score,
                    )
                    for chunk in chunks
                    if chunk.chunk_id in analysis_answer.evidence_chunk_ids
                ],
            )

        # document route
        plan = await self.query_planning_service.plan(question)

        chunks = self.retrieval_service.retrieve(
            research=research,
            query_text=plan.query_text,
            num_results=3,
        )

        is_sufficient = await self.context_sufficiency_service.is_sufficient(
            question=question,
            chunks=chunks,
        )

        if not is_sufficient:
            return CompanyDocumentQAResult(
                name=name,
                question=question,
                query_text=plan.query_text,
                answer=(
                    "取得した資料には、この質問に回答するための十分な情報がありません。"
                ),
                evidence_chunk_ids=[],
                insufficient_context=True,
                sources=[],
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
