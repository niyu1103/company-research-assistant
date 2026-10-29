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
        specific_year_values: dict[int, FinancialYearValue] | None = None,
    ) -> FinancialQuestionAnswer:
        if plan.specific_years:
            return self._answer_specific_years(
                research=research,
                history=history,
                plan=plan,
                specific_year_values=specific_year_values,
            )

        if plan.is_overall_performance:
            return self._answer_overall_performance(
                research=research,
                history=history,
                years=plan.years or 5,
            )

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

    def find_missing_specific_years(
        self,
        *,
        research: CompanyResearchResult,
        history: FinancialHistory,
        plan: FinancialQuestionPlan,
    ) -> list[int]:
        if not plan.specific_years:
            return []

        period_end = research.annual_report.period_end

        if period_end is None:
            return list(plan.specific_years)

        if plan.metric is not None:
            values = self._get_values(
                history=history,
                metric=plan.metric,
            )
        else:
            values = history.revenue

        available_years = {
            period_end.year - self._period_offset(value.context_id) for value in values
        }

        return [year for year in plan.specific_years if year not in available_years]

    def _answer_specific_years(
        self,
        *,
        research: CompanyResearchResult,
        history: FinancialHistory,
        plan: FinancialQuestionPlan,
        specific_year_values: dict[int, FinancialYearValue] | None = None,
    ) -> FinancialQuestionAnswer:
        if plan.metric is None:
            return FinancialQuestionAnswer(
                answer=("比較する財務指標を特定できませんでした。"),
                insufficient_context=True,
            )

        period_end = research.annual_report.period_end

        if period_end is None:
            return FinancialQuestionAnswer(
                answer=("対象年度を判定するための決算期情報を取得できませんでした。"),
                insufficient_context=True,
            )

        values = self._get_values(
            history=history,
            metric=plan.metric,
        )

        values_by_year = {
            (period_end.year - self._period_offset(value.context_id)): value
            for value in values
        }

        if specific_year_values:
            values_by_year.update(specific_year_values)

        selected_values: list[tuple[int, FinancialYearValue]] = []

        for year in plan.specific_years:
            value = values_by_year.get(year)

            if value is None:
                return FinancialQuestionAnswer(
                    answer=(
                        f"{year}年の"
                        f"{self._metric_name(plan.metric)}を"
                        "取得できませんでした。"
                    ),
                    insufficient_context=True,
                )

            selected_values.append(
                (
                    year,
                    value,
                )
            )

        metric_name = self._metric_name(plan.metric)

        lines = [
            (
                f"{year}年{period_end.month}月期: "
                f"{self.analysis_service.format_yen(value.value)}"
            )
            for year, value in selected_values
        ]

        answer = (
            f"{research.company.name}の"
            f"{metric_name}は以下のとおりです。\n\n" + "\n".join(lines)
        )

        if len(selected_values) == 2:
            first_year, first_value = selected_values[0]
            second_year, second_value = selected_values[1]

            difference = second_value.value - first_value.value

            if difference > 0:
                answer += (
                    "\n\n"
                    f"{second_year}年{period_end.month}月期は"
                    f"{first_year}年{period_end.month}月期と比べて"
                    f"{self.analysis_service.format_yen(difference)}"
                    "増加しています。"
                )

            elif difference < 0:
                answer += (
                    "\n\n"
                    f"{second_year}年{period_end.month}月期は"
                    f"{first_year}年{period_end.month}月期と比べて"
                    f"{self.analysis_service.format_yen(abs(difference))}"
                    "減少しています。"
                )

            else:
                answer += (
                    "\n\n"
                    f"{first_year}年{period_end.month}月期と"
                    f"{second_year}年{period_end.month}月期の"
                    f"{metric_name}は同額です。"
                )

        return FinancialQuestionAnswer(
            answer=answer,
            insufficient_context=False,
        )

    def _answer_overall_performance(
        self,
        *,
        research: CompanyResearchResult,
        history: FinancialHistory,
        years: int,
    ) -> FinancialQuestionAnswer:
        metric_histories: list[tuple[str, list[FinancialYearValue]]] = [
            (
                "売上高",
                history.revenue,
            ),
            (
                "営業利益",
                history.operating_income,
            ),
            (
                "経常利益",
                history.ordinary_income,
            ),
            (
                "純利益",
                history.net_income,
            ),
        ]

        lines: list[str] = []

        available_periods = max(
            (min(len(values), years) for _, values in metric_histories if values),
            default=0,
        )

        for metric_name, values in metric_histories:
            if not values:
                continue

            selected_values = values[-years:]

            formatted_values = [
                (
                    f"{self._period_name(research=research, value=value)} "
                    f"{self.analysis_service.format_yen(value.value)}"
                )
                for value in selected_values
            ]

            lines.append(f"{metric_name}: " + " → ".join(formatted_values))

        if not lines:
            return FinancialQuestionAnswer(
                answer=("業績を確認するための財務データを取得できませんでした。"),
                insufficient_context=True,
            )

        return FinancialQuestionAnswer(
            answer=(
                f"{research.company.name}の"
                f"取得できた直近最大{available_periods}期分の"
                "業績は以下のとおりです。\n\n" + "\n".join(lines)
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
            len(history.ordinary_income),
            len(history.profit_before_tax),
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

    def find_current_metric_value(
        self,
        *,
        history: FinancialHistory,
        metric: FinancialMetric,
    ) -> FinancialYearValue | None:
        values = self._get_values(
            history=history,
            metric=metric,
        )

        return self._find_current(values)

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
