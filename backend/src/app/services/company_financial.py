from app.models.financial import (
    FinancialHistory,
    FinancialYearValue,
)
from app.models.financial_question import (
    FinancialMetric,
    FinancialQuestionAnswer,
    FinancialQuestionPlan,
)
from app.models.research import CompanyResearchResult
from app.services.company_analysis import (
    CompanyAnalysisService,
)


class CompanyFinancialService:
    def __init__(self) -> None:
        self.analysis_service = CompanyAnalysisService()

    def answer(
        self,
        *,
        research: CompanyResearchResult,
        history: FinancialHistory,
        plan: FinancialQuestionPlan,
    ) -> FinancialQuestionAnswer:
        if plan.operation == "available_periods":
            return self._answer_available_periods(
                history=history,
                metric=plan.metric,
            )

        if plan.metric is None:
            return FinancialQuestionAnswer(
                answer=("質問の対象となる財務指標を特定できませんでした。"),
                insufficient_context=True,
            )

        values = self._get_values(
            history=history,
            metric=plan.metric,
        )

        if not values:
            return FinancialQuestionAnswer(
                answer=("質問に必要な財務データを取得できませんでした。"),
                insufficient_context=True,
            )

        if plan.years is not None and plan.years > len(values):
            return FinancialQuestionAnswer(
                answer=(
                    f"現在取得できている"
                    f"{self._metric_name(plan.metric)}は"
                    f"{len(values)}期分のため、"
                    f"過去{plan.years}期については"
                    "判定できません。"
                ),
                insufficient_context=True,
            )

        if plan.operation == "current":
            value = self._find_current(values)

            if value is None:
                return FinancialQuestionAnswer(
                    answer=("最新年度の財務データを取得できませんでした。"),
                    insufficient_context=True,
                )

            return FinancialQuestionAnswer(
                answer=self._build_answer(
                    research=research,
                    plan=plan,
                    value=value,
                ),
                insufficient_context=False,
            )

        selected_values = values

        if plan.years is not None:
            selected_values = values[-plan.years :]

        if plan.operation == "max":
            value = max(
                selected_values,
                key=lambda item: item.value,
            )
        else:
            value = min(
                selected_values,
                key=lambda item: item.value,
            )

        return FinancialQuestionAnswer(
            answer=self._build_answer(
                research=research,
                plan=plan,
                value=value,
            ),
            insufficient_context=False,
        )

    def _answer_available_periods(
        self,
        *,
        history: FinancialHistory,
        metric: FinancialMetric | None,
    ) -> FinancialQuestionAnswer:
        if metric is not None:
            values = self._get_values(
                history=history,
                metric=metric,
            )

            return FinancialQuestionAnswer(
                answer=(
                    f"{self._metric_name(metric)}は現在{len(values)}期分取得できます。"
                ),
                insufficient_context=False,
            )

        counts = [
            len(history.revenue),
            len(history.operating_income),
            len(history.net_income),
            len(history.total_assets),
            len(history.operating_cash_flow),
        ]

        available_periods = max(
            counts,
            default=0,
        )

        if available_periods == 0:
            return FinancialQuestionAnswer(
                answer=("取得できる財務履歴がありません。"),
                insufficient_context=True,
            )

        return FinancialQuestionAnswer(
            answer=(
                "現在取得できる財務履歴は"
                f"最大{available_periods}期分です。"
                "指標によって取得できる期数が"
                "異なる場合があります。"
            ),
            insufficient_context=False,
        )

    def _get_values(
        self,
        *,
        history: FinancialHistory,
        metric: FinancialMetric,
    ) -> list[FinancialYearValue]:
        if metric == "revenue":
            return history.revenue

        if metric == "operating_income":
            return history.operating_income

        if metric == "net_income":
            return history.net_income

        if metric == "total_assets":
            return history.total_assets

        return history.operating_cash_flow

    def _find_current(
        self,
        values: list[FinancialYearValue],
    ) -> FinancialYearValue | None:
        for value in values:
            if value.context_id.startswith("CurrentYear"):
                return value

        return None

    def _build_answer(
        self,
        *,
        research: CompanyResearchResult,
        plan: FinancialQuestionPlan,
        value: FinancialYearValue,
    ) -> str:
        if plan.metric is None:
            return "財務指標を特定できませんでした。"

        amount = self.analysis_service.format_yen(value.value)

        metric_name = self._metric_name(plan.metric)

        period = self._period_name(
            research=research,
            value=value,
        )

        return f"{research.company.name}の{metric_name}は、{period}の{amount}です。"

    def _metric_name(
        self,
        metric: FinancialMetric,
    ) -> str:
        if metric == "revenue":
            return "売上高"

        if metric == "operating_income":
            return "営業利益"

        if metric == "net_income":
            return "純利益"

        if metric == "total_assets":
            return "総資産"

        return "営業キャッシュフロー"

    def _period_name(
        self,
        *,
        research: CompanyResearchResult,
        value: FinancialYearValue,
    ) -> str:
        period_end = research.annual_report.period_end

        if period_end is None:
            return value.relative_year

        offset = self._period_offset(value.context_id)

        year = period_end.year - offset

        return f"{year}年{period_end.month}月期"

    def _period_offset(
        self,
        context_id: str,
    ) -> int:
        if context_id.startswith("Prior4Year"):
            return 4

        if context_id.startswith("Prior3Year"):
            return 3

        if context_id.startswith("Prior2Year"):
            return 2

        if context_id.startswith("Prior1Year"):
            return 1

        return 0
