import logging

from agents import Agent, Runner, set_default_openai_key

from app.models.financial import (
    FinancialHistory,
    FinancialTrend,
    FinancialTrendYear,
    FinancialYearValue,
)
from app.models.research import CompanyResearchResult
from app.models.research_analysis import (
    CompanyAnalysis,
    CompanyAnalysisInput,
    CompanyAnalysisResearch,
    CompanyNarrativeAnalysis,
    FinancialAnalysis,
    FinancialDerivedMetrics,
    FinancialDisplayValues,
)
from app.settings import get_settings

logger = logging.getLogger("uvicorn.error")

company_analysis_agent = Agent(
    name="Company Research Analyst",
    model="gpt-5.6-luna",
    instructions="""
あなたは企業リサーチアナリストです。

入力として与えられた企業情報のみを根拠に分析してください。

推測や外部知識を追加しないでください。
入力データに存在しない情報は断定しないでください。

事業内容を整理する際は、
入力に記載されている販売地域、販売主体、
開発・製造・販売の役割分担など、
事業体制に関する重要な事実も可能な限り保持してください。

事業リスクを整理する際は、
入力に含まれる独立したリスク項目を
できるだけ取りこぼさないでください。

複数のリスクを1つのカテゴリにまとめても構いませんが、
まとめることで個別の重要なリスクが消えないようにしてください。

入力に明示されているリスクについては、
関連する別のリスクに吸収して省略せず、
少なくともいずれかの risks.summary に
内容が分かる形で残してください。

特に、同じ事業活動に関連していても、
発生原因や影響が異なるリスクは
別の事実として扱ってください。

以下を整理してください。

- 事業内容の要約
- 主な製品・サービス
- 事業の特徴
- 主な事業リスク

日本語で簡潔に回答してください。
""",
    output_type=CompanyNarrativeAnalysis,
)


class CompanyAnalysisService:
    def calculate_derived_financials(
        self,
        research: CompanyResearchResult,
    ) -> FinancialDerivedMetrics:
        financials = research.financials

        revenue = financials.revenue.value if financials.revenue is not None else None

        operating_income = (
            financials.operating_income.value
            if financials.operating_income is not None
            else None
        )

        net_income = (
            financials.net_income.value if financials.net_income is not None else None
        )

        operating_cash_flow = (
            financials.operating_cash_flow.value
            if financials.operating_cash_flow is not None
            else None
        )

        if revenue is None or revenue == 0:
            return FinancialDerivedMetrics()

        return FinancialDerivedMetrics(
            operating_margin=(
                round(
                    operating_income / revenue * 100,
                    2,
                )
                if operating_income is not None
                else None
            ),
            net_margin=(
                round(
                    net_income / revenue * 100,
                    2,
                )
                if net_income is not None
                else None
            ),
            operating_cash_flow_margin=(
                round(
                    operating_cash_flow / revenue * 100,
                    2,
                )
                if operating_cash_flow is not None
                else None
            ),
        )

    async def analyze(
        self,
        research: CompanyResearchResult,
        display_financials: FinancialDisplayValues,
        financial_trend: FinancialTrend,
    ) -> CompanyAnalysis:
        settings = get_settings()

        set_default_openai_key(settings.openai_api_key)

        business_risks = self.prepare_business_risks(research.narratives.business_risks)

        analysis_input = CompanyAnalysisInput(
            research=CompanyAnalysisResearch(
                company_name=research.company.name,
                business_overview=research.narratives.business_overview,
                business_risks=business_risks,
            ),
        )

        input_json = analysis_input.model_dump_json(ensure_ascii=False)

        logger.info(
            "AI input chars: %d",
            len(input_json),
        )

        logger.info(
            "AI business overview chars: %d",
            len(research.narratives.business_overview or ""),
        )

        result = await Runner.run(
            company_analysis_agent,
            input=input_json,
        )

        usage = result.context_wrapper.usage

        logger.info(
            "AI requests: %d",
            usage.requests,
        )

        logger.info(
            "AI input tokens: %d",
            usage.input_tokens,
        )

        logger.info(
            "AI output tokens: %d",
            usage.output_tokens,
        )

        logger.info(
            "AI total tokens: %d",
            usage.total_tokens,
        )

        narrative_analysis = CompanyNarrativeAnalysis.model_validate(
            result.final_output
        )

        financial_analysis = self.build_financial_analysis(
            display_financials=display_financials,
            financial_trend=financial_trend,
        )

        return CompanyAnalysis(
            business=narrative_analysis.business,
            risks=narrative_analysis.risks,
            financials=financial_analysis,
        )

    def format_yen(
        self,
        value: int | None,
    ) -> str | None:
        if value is None:
            return None

        if value == 0:
            return "0円"

        sign = "-" if value < 0 else ""
        amount = abs(value)

        cho, remainder = divmod(
            amount,
            1_000_000_000_000,
        )
        oku, remainder = divmod(
            remainder,
            100_000_000,
        )
        man, yen = divmod(
            remainder,
            10_000,
        )

        parts: list[str] = []

        if cho:
            parts.append(f"{cho:,}兆")

        if oku:
            parts.append(f"{oku:,}億")

        if man:
            parts.append(f"{man:,}万")

        if yen:
            parts.append(f"{yen:,}")

        return f"{sign}{''.join(parts)}円"

    def build_financial_display_values(
        self,
        research: CompanyResearchResult,
    ) -> FinancialDisplayValues:
        financials = research.financials

        return FinancialDisplayValues(
            revenue=self.format_yen(
                financials.revenue.value if financials.revenue is not None else None
            ),
            operating_income=self.format_yen(
                financials.operating_income.value
                if financials.operating_income is not None
                else None
            ),
            profit_before_tax=self.format_yen(
                financials.profit_before_tax.value
                if financials.profit_before_tax is not None
                else None
            ),
            net_income=self.format_yen(
                financials.net_income.value
                if financials.net_income is not None
                else None
            ),
            total_assets=self.format_yen(
                financials.total_assets.value
                if financials.total_assets is not None
                else None
            ),
            operating_cash_flow=self.format_yen(
                financials.operating_cash_flow.value
                if financials.operating_cash_flow is not None
                else None
            ),
        )

    def _get_history_value(
        self,
        values: list[FinancialYearValue],
        period_prefix: str,
    ) -> int | None:
        for item in values:
            if item.context_id.startswith(period_prefix):
                return item.value

        return None

    def _calculate_growth_rate(
        self,
        current: int | None,
        previous: int | None,
    ) -> float | None:
        if current is None or previous is None:
            return None

        if previous == 0:
            return None

        return round(
            (current - previous) / previous * 100,
            2,
        )

    def _calculate_margin(
        self,
        value: int | None,
        revenue: int | None,
    ) -> float | None:
        if value is None or revenue in (None, 0):
            return None

        return round(
            value / revenue * 100,
            2,
        )

    def build_financial_trend(
        self,
        history: FinancialHistory,
    ) -> FinancialTrend:
        periods = (
            ("Prior4Year", "四期前"),
            ("Prior3Year", "三期前"),
            ("Prior2Year", "前々期"),
            ("Prior1Year", "前期"),
            ("CurrentYear", "当期"),
        )

        years: list[FinancialTrendYear] = []

        for period_prefix, relative_year in periods:
            revenue = self._get_history_value(
                history.revenue,
                period_prefix,
            )
            operating_income = self._get_history_value(
                history.operating_income,
                period_prefix,
            )
            profit_before_tax = self._get_history_value(
                history.profit_before_tax,
                period_prefix,
            )
            net_income = self._get_history_value(
                history.net_income,
                period_prefix,
            )
            total_assets = self._get_history_value(
                history.total_assets,
                period_prefix,
            )
            operating_cash_flow = self._get_history_value(
                history.operating_cash_flow,
                period_prefix,
            )

            years.append(
                FinancialTrendYear(
                    relative_year=relative_year,
                    revenue=revenue,
                    operating_income=operating_income,
                    profit_before_tax=profit_before_tax,
                    net_income=net_income,
                    total_assets=total_assets,
                    operating_cash_flow=operating_cash_flow,
                    operating_margin=self._calculate_margin(
                        operating_income,
                        revenue,
                    ),
                    net_margin=self._calculate_margin(
                        net_income,
                        revenue,
                    ),
                    operating_cash_flow_margin=self._calculate_margin(
                        operating_cash_flow,
                        revenue,
                    ),
                )
            )

        for index in range(1, len(years)):
            current = years[index]
            previous = years[index - 1]

            current.revenue_growth_rate = self._calculate_growth_rate(
                current.revenue,
                previous.revenue,
            )

            current.operating_income_growth_rate = self._calculate_growth_rate(
                current.operating_income,
                previous.operating_income,
            )

            current.net_income_growth_rate = self._calculate_growth_rate(
                current.net_income,
                previous.net_income,
            )

        return FinancialTrend(years=years)

    def prepare_business_risks(
        self,
        text: str | None,
    ) -> str | None:
        if text is None:
            return None

        text = text.strip()

        if not text:
            return None

        return text

    def build_financial_analysis(
        self,
        display_financials: FinancialDisplayValues,
        financial_trend: FinancialTrend,
    ) -> FinancialAnalysis:
        summary_parts: list[str] = []

        if display_financials.revenue is not None:
            summary_parts.append(f"売上は{display_financials.revenue}")

        if display_financials.operating_income is not None:
            summary_parts.append(f"営業利益は{display_financials.operating_income}")

        if display_financials.profit_before_tax is not None:
            summary_parts.append(f"税引前利益は{display_financials.profit_before_tax}")

        if display_financials.net_income is not None:
            summary_parts.append(f"純利益は{display_financials.net_income}")

        if display_financials.total_assets is not None:
            summary_parts.append(f"総資産は{display_financials.total_assets}")

        if display_financials.operating_cash_flow is not None:
            summary_parts.append(
                "営業活動によるキャッシュ・フローは"
                f"{display_financials.operating_cash_flow}"
            )

        summary = "、".join(summary_parts)

        if summary:
            summary += "です。"

        notable_points: list[str] = []

        if len(financial_trend.years) < 2:
            return FinancialAnalysis(
                summary=summary,
                notable_points=notable_points,
            )

        previous = financial_trend.years[-2]
        current = financial_trend.years[-1]

        # 売上
        if current.revenue_growth_rate is not None:
            if current.revenue_growth_rate > 0:
                notable_points.append(
                    f"売上は前期比{current.revenue_growth_rate:.2f}%増加しました。"
                )
            elif current.revenue_growth_rate < 0:
                notable_points.append(
                    f"売上は前期比{abs(current.revenue_growth_rate):.2f}%減少しました。"
                )
            else:
                notable_points.append("売上は前期比横ばいでした。")

        # 営業利益・営業利益率
        if current.operating_income_growth_rate is not None:
            if current.operating_income_growth_rate > 0:
                text = (
                    "営業利益は前期比"
                    f"{current.operating_income_growth_rate:.2f}%"
                    "増加しました"
                )
            elif current.operating_income_growth_rate < 0:
                text = (
                    "営業利益は前期比"
                    f"{abs(current.operating_income_growth_rate):.2f}%"
                    "減少しました"
                )
            else:
                text = "営業利益は前期比横ばいでした"

            if (
                previous.operating_margin is not None
                and current.operating_margin is not None
            ):
                if current.operating_margin > previous.operating_margin:
                    text += (
                        "。営業利益率は"
                        f"{previous.operating_margin:.2f}%から"
                        f"{current.operating_margin:.2f}%に"
                        "上昇しました"
                    )
                elif current.operating_margin < previous.operating_margin:
                    text += (
                        "。営業利益率は"
                        f"{previous.operating_margin:.2f}%から"
                        f"{current.operating_margin:.2f}%に"
                        "低下しました"
                    )
                else:
                    text += (
                        f"。営業利益率は{current.operating_margin:.2f}%で横ばいでした"
                    )

            notable_points.append(f"{text}。")

        # 純利益・純利益率
        if current.net_income_growth_rate is not None:
            if current.net_income_growth_rate > 0:
                text = (
                    f"純利益は前期比{current.net_income_growth_rate:.2f}%増加しました"
                )
            elif current.net_income_growth_rate < 0:
                text = (
                    "純利益は前期比"
                    f"{abs(current.net_income_growth_rate):.2f}%"
                    "減少しました"
                )
            else:
                text = "純利益は前期比横ばいでした"

            if previous.net_margin is not None and current.net_margin is not None:
                if current.net_margin > previous.net_margin:
                    text += (
                        "。純利益率は"
                        f"{previous.net_margin:.2f}%から"
                        f"{current.net_margin:.2f}%に"
                        "上昇しました"
                    )
                elif current.net_margin < previous.net_margin:
                    text += (
                        "。純利益率は"
                        f"{previous.net_margin:.2f}%から"
                        f"{current.net_margin:.2f}%に"
                        "低下しました"
                    )
                else:
                    text += f"。純利益率は{current.net_margin:.2f}%で横ばいでした"

            notable_points.append(f"{text}。")

        # 営業キャッシュフロー・マージン
        if (
            previous.operating_cash_flow_margin is not None
            and current.operating_cash_flow_margin is not None
        ):
            if current.operating_cash_flow_margin > previous.operating_cash_flow_margin:
                notable_points.append(
                    "営業活動によるキャッシュ・フロー・マージンは"
                    f"{previous.operating_cash_flow_margin:.2f}%から"
                    f"{current.operating_cash_flow_margin:.2f}%に"
                    "上昇しました。"
                )
            elif (
                current.operating_cash_flow_margin < previous.operating_cash_flow_margin
            ):
                notable_points.append(
                    "営業活動によるキャッシュ・フロー・マージンは"
                    f"{previous.operating_cash_flow_margin:.2f}%から"
                    f"{current.operating_cash_flow_margin:.2f}%に"
                    "低下しました。"
                )
            else:
                notable_points.append(
                    "営業活動によるキャッシュ・フロー・マージンは"
                    f"{current.operating_cash_flow_margin:.2f}%で"
                    "横ばいでした。"
                )

        # 総資産
        if previous.total_assets is not None and current.total_assets is not None:
            previous_assets = self.format_yen(previous.total_assets)
            current_assets = self.format_yen(current.total_assets)

            if previous_assets is not None and current_assets is not None:
                if current.total_assets > previous.total_assets:
                    notable_points.append(
                        f"総資産は前期の{previous_assets}から"
                        f"{current_assets}に増加しました。"
                    )
                elif current.total_assets < previous.total_assets:
                    notable_points.append(
                        f"総資産は前期の{previous_assets}から"
                        f"{current_assets}に減少しました。"
                    )
                else:
                    notable_points.append(
                        f"総資産は前期と同額の{current_assets}でした。"
                    )

        return FinancialAnalysis(
            summary=summary,
            notable_points=notable_points,
        )
