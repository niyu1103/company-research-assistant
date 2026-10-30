import re

from anyio import to_thread

from app.clients.edinet import EdinetClient
from app.models.conversation_state import ConversationState
from app.models.document_qa import (
    CompanyDocumentQAAction,
    CompanyDocumentQAOption,
    CompanyDocumentQAResult,
    CompanyDocumentQASource,
)
from app.models.financial import FinancialYearValue
from app.models.financial_question import (
    FinancialQuestionPlan,
)
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
from app.services.conversation_state import (
    ConversationStateService,
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
from app.services.historical_period_resolver import (
    HistoricalPeriodResolverService,
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
        historical_period_resolver_service: HistoricalPeriodResolverService
        | None = None,
        conversation_state_service: ConversationStateService | None = None,
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
        self.historical_period_resolver_service = historical_period_resolver_service
        self.conversation_state_service = conversation_state_service

    async def answer(
        self,
        *,
        name: str,
        question: str,
        conversation_id: str = "",
        action: CompanyDocumentQAAction | None = None,
    ) -> CompanyDocumentQAResult:
        confirmed_financial_plan: FinancialQuestionPlan | None = None

        if conversation_id and self.conversation_state_service is not None:
            state = self.conversation_state_service.get(conversation_id)

            if state is not None and state.awaiting_period_confirmation:
                if (
                    state.financial_plan is None
                    or state.company_name is None
                    or state.original_question is None
                ):
                    self.conversation_state_service.delete(conversation_id)

                    return CompanyDocumentQAResult(
                        name=name,
                        question=question,
                        query_text=question,
                        answer=(
                            "会話状態を復元できませんでした。"
                            "元の質問をもう一度入力してください。"
                        ),
                        evidence_chunk_ids=[],
                        insufficient_context=True,
                        sources=[],
                        conversation_id=conversation_id,
                    )

                matched_years = re.findall(
                    r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})年?",
                    question,
                )

                #
                # 範囲外期間の再確認中
                #
                if state.pending_action == "confirm_period_override":
                    if action == "use_resolved_period":
                        if (
                            state.proposed_start_year is None
                            or state.proposed_end_year is None
                        ):
                            self.conversation_state_service.delete(conversation_id)

                            return CompanyDocumentQAResult(
                                name=name,
                                question=question,
                                query_text=question,
                                answer=(
                                    "会話状態を復元できませんでした。"
                                    "元の質問をもう一度入力してください。"
                                ),
                                evidence_chunk_ids=[],
                                insufficient_context=True,
                                sources=[],
                                conversation_id=conversation_id,
                            )

                        resolved_years = [
                            state.proposed_start_year,
                        ]

                        if state.proposed_end_year != state.proposed_start_year:
                            resolved_years.append(state.proposed_end_year)

                        confirmed_financial_plan = state.financial_plan.model_copy(
                            update={
                                "period_hint": (state.period_label),
                                "specific_years": (resolved_years),
                            }
                        )

                        name = state.company_name
                        question = state.original_question

                        self.conversation_state_service.delete(conversation_id)

                    elif action == "use_requested_period":
                        if (
                            state.requested_start_year is None
                            or state.requested_end_year is None
                        ):
                            self.conversation_state_service.delete(conversation_id)

                            return CompanyDocumentQAResult(
                                name=name,
                                question=question,
                                query_text=question,
                                answer=(
                                    "会話状態を復元できませんでした。"
                                    "元の質問をもう一度入力してください。"
                                ),
                                evidence_chunk_ids=[],
                                insufficient_context=True,
                                sources=[],
                                conversation_id=conversation_id,
                            )

                        resolved_years = [
                            state.requested_start_year,
                        ]

                        if state.requested_end_year != state.requested_start_year:
                            resolved_years.append(state.requested_end_year)

                        confirmed_financial_plan = state.financial_plan.model_copy(
                            update={
                                "period_hint": (
                                    f"{state.requested_start_year}年〜"
                                    f"{state.requested_end_year}年"
                                ),
                                "specific_years": (resolved_years),
                            }
                        )

                        name = state.company_name
                        question = state.original_question

                        self.conversation_state_service.delete(conversation_id)

                    elif action != "change_period" and len(matched_years) < 2:
                        return CompanyDocumentQAResult(
                            name=state.company_name,
                            question=question,
                            query_text=question,
                            answer=(
                                f"指定された"
                                f"{state.requested_start_year}年〜"
                                f"{state.requested_end_year}年には、"
                                f"{state.period_label or '元の期間'}"
                                "として解釈した"
                                f"{state.proposed_start_year}年〜"
                                f"{state.proposed_end_year}年の"
                                "範囲外が含まれています。"
                                "どの期間を使用しますか？"
                            ),
                            evidence_chunk_ids=[],
                            insufficient_context=False,
                            sources=[],
                            conversation_id=conversation_id,
                            requires_user_input=True,
                            input_type="period_scope_confirmation",
                            options=[
                                CompanyDocumentQAOption(
                                    label=(
                                        f"{state.proposed_start_year}年〜"
                                        f"{state.proposed_end_year}年"
                                        "で確認する"
                                    ),
                                    value="use_resolved_period",
                                ),
                                CompanyDocumentQAOption(
                                    label=(
                                        f"{state.requested_start_year}年〜"
                                        f"{state.requested_end_year}年"
                                        "のまま確認する"
                                    ),
                                    value="use_requested_period",
                                ),
                                CompanyDocumentQAOption(
                                    label="別の期間を入力する",
                                    value="change_period",
                                ),
                            ],
                        )

                #
                # まだ期間が確定していない場合
                #
                if confirmed_financial_plan is None:
                    is_period_change = (
                        action == "change_period"
                        or state.pending_action == "change_period"
                        or (
                            state.pending_action
                            in {
                                "confirm_period",
                                "confirm_period_override",
                            }
                            and len(matched_years) >= 2
                        )
                    )

                    if is_period_change:
                        if len(matched_years) < 2:
                            already_waiting_for_period = (
                                state.pending_action == "change_period"
                                and action != "change_period"
                            )

                            updated_state = state.model_copy(
                                update={
                                    "pending_action": "change_period",
                                    "confirmation_type": "period",
                                    "requested_start_year": None,
                                    "requested_end_year": None,
                                }
                            )

                            self.conversation_state_service.save(updated_state)

                            if already_waiting_for_period:
                                response_message = (
                                    "開始年と終了年を確認できませんでした。"
                                    "「2021年〜2023年」のように"
                                    "入力してください。"
                                )
                            else:
                                response_message = (
                                    "比較したい期間を"
                                    "「2020年〜2022年」のように"
                                    "入力してください。"
                                )

                            return CompanyDocumentQAResult(
                                name=state.company_name,
                                question=question,
                                query_text=question,
                                answer=response_message,
                                evidence_chunk_ids=[],
                                insufficient_context=False,
                                sources=[],
                                conversation_id=conversation_id,
                                requires_user_input=True,
                                input_type="period_range",
                                options=[],
                            )

                        start_year = int(matched_years[0])
                        end_year = int(matched_years[1])

                        if start_year > end_year:
                            return CompanyDocumentQAResult(
                                name=state.company_name,
                                question=question,
                                query_text=question,
                                answer=(
                                    "開始年が終了年より後に"
                                    "なっています。"
                                    "「2021年〜2023年」のように"
                                    "入力してください。"
                                ),
                                evidence_chunk_ids=[],
                                insufficient_context=False,
                                sources=[],
                                conversation_id=conversation_id,
                                requires_user_input=True,
                                input_type="period_range",
                                options=[],
                            )

                        outside_resolved_period = (
                            state.proposed_start_year is not None
                            and state.proposed_end_year is not None
                            and (
                                start_year < state.proposed_start_year
                                or end_year > state.proposed_end_year
                            )
                        )

                        if outside_resolved_period:
                            updated_state = state.model_copy(
                                update={
                                    "pending_action": ("confirm_period_override"),
                                    "confirmation_type": ("period_override"),
                                    "requested_start_year": (start_year),
                                    "requested_end_year": (end_year),
                                }
                            )

                            self.conversation_state_service.save(updated_state)

                            return CompanyDocumentQAResult(
                                name=state.company_name,
                                question=question,
                                query_text=question,
                                answer=(
                                    f"指定された"
                                    f"{start_year}年〜"
                                    f"{end_year}年には、"
                                    f"{state.period_label or '元の期間'}"
                                    "として解釈した"
                                    f"{state.proposed_start_year}年〜"
                                    f"{state.proposed_end_year}年の"
                                    "範囲外が含まれています。"
                                    "どの期間を使用しますか？"
                                ),
                                evidence_chunk_ids=[],
                                insufficient_context=False,
                                sources=[],
                                conversation_id=conversation_id,
                                requires_user_input=True,
                                input_type=("period_scope_confirmation"),
                                options=[
                                    CompanyDocumentQAOption(
                                        label=(
                                            f"{state.proposed_start_year}年〜"
                                            f"{state.proposed_end_year}年"
                                            "で確認する"
                                        ),
                                        value=("use_resolved_period"),
                                    ),
                                    CompanyDocumentQAOption(
                                        label=(
                                            f"{start_year}年〜"
                                            f"{end_year}年"
                                            "のまま確認する"
                                        ),
                                        value=("use_requested_period"),
                                    ),
                                    CompanyDocumentQAOption(
                                        label=("別の期間を入力する"),
                                        value="change_period",
                                    ),
                                ],
                            )

                        #
                        # 変更された期間が
                        # Resolverの範囲内ならそのまま確定
                        #
                        resolved_years = [
                            start_year,
                        ]

                        if end_year != start_year:
                            resolved_years.append(end_year)

                        confirmed_financial_plan = state.financial_plan.model_copy(
                            update={
                                "period_hint": (f"{start_year}年〜{end_year}年"),
                                "specific_years": (resolved_years),
                            }
                        )

                        name = state.company_name
                        question = state.original_question

                        self.conversation_state_service.delete(conversation_id)

                #
                # Resolverが提案した期間を
                # ユーザーがそのまま承認
                #
                if confirmed_financial_plan is None:
                    normalized_answer = question.strip().lower().rstrip("。")

                    confirmed = action == "confirm_period" or normalized_answer in {
                        "はい",
                        "ok",
                        "お願いします",
                        "それでお願いします",
                        "その期間でお願いします",
                    }

                    if confirmed and state.pending_action == "confirm_period":
                        if (
                            state.proposed_start_year is None
                            or state.proposed_end_year is None
                        ):
                            self.conversation_state_service.delete(conversation_id)

                            return CompanyDocumentQAResult(
                                name=name,
                                question=question,
                                query_text=question,
                                answer=(
                                    "会話状態を復元できませんでした。"
                                    "元の質問をもう一度入力してください。"
                                ),
                                evidence_chunk_ids=[],
                                insufficient_context=True,
                                sources=[],
                                conversation_id=conversation_id,
                            )

                        resolved_years = [
                            state.proposed_start_year,
                        ]

                        if state.proposed_end_year != state.proposed_start_year:
                            resolved_years.append(state.proposed_end_year)

                        confirmed_financial_plan = state.financial_plan.model_copy(
                            update={
                                "period_hint": (state.period_label),
                                "specific_years": (resolved_years),
                            }
                        )

                        name = state.company_name
                        question = state.original_question

                        self.conversation_state_service.delete(conversation_id)

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
            if confirmed_financial_plan is not None:
                financial_plan = confirmed_financial_plan
            else:
                financial_plan = await self.financial_question_planner_service.plan(
                    question
                )

            if (
                financial_plan.requires_specific_period
                and not financial_plan.specific_years
                and financial_plan.period_hint is not None
                and self.historical_period_resolver_service is not None
            ):
                period_resolution = (
                    await self.historical_period_resolver_service.resolve(
                        financial_plan.period_hint
                    )
                )

                if (
                    period_resolution.resolved
                    and period_resolution.start_year is not None
                    and period_resolution.end_year is not None
                ):
                    if conversation_id and self.conversation_state_service is not None:
                        state = ConversationState(
                            conversation_id=conversation_id,
                            company_name=name,
                            original_question=question,
                            financial_plan=financial_plan,
                            awaiting_period_confirmation=True,
                            pending_action="confirm_period",
                            confirmation_type="period",
                            period_label=period_resolution.label,
                            proposed_start_year=(period_resolution.start_year),
                            proposed_end_year=(period_resolution.end_year),
                            period_resolution_reason=(period_resolution.reason),
                        )

                        self.conversation_state_service.save(state)

                        return CompanyDocumentQAResult(
                            name=name,
                            question=question,
                            query_text=question,
                            answer=(
                                f"{period_resolution.label}を"
                                f"{period_resolution.start_year}年〜"
                                f"{period_resolution.end_year}年として"
                                "比較してよいですか？"
                            ),
                            evidence_chunk_ids=[],
                            insufficient_context=False,
                            sources=[],
                            conversation_id=conversation_id,
                            requires_user_input=True,
                            input_type="period_confirmation",
                            options=[
                                CompanyDocumentQAOption(
                                    label="はい、この期間で比較する",
                                    value="confirm_period",
                                ),
                                CompanyDocumentQAOption(
                                    label="期間を変更する",
                                    value="change_period",
                                ),
                            ],
                        )

                    resolved_years = [period_resolution.start_year]

                    if period_resolution.end_year != period_resolution.start_year:
                        resolved_years.append(period_resolution.end_year)

                    financial_plan = financial_plan.model_copy(
                        update={
                            "period_hint": period_resolution.label,
                            "specific_years": resolved_years,
                        }
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
