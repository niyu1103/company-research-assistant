import re

from agents import Agent, Runner

from app.models.financial_question import (
    FinancialQuestionPlan,
)


class FinancialQuestionPlannerService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Financial Question Planner",
            model="gpt-5.6-luna",
            instructions="""
あなたは企業財務質問を構造化するPlannerです。

質問から以下を判定してください。

metric:
- revenue: 売上、売上高、売上収益
- operating_income: 営業利益
- net_income: 純利益、当期純利益
- total_assets: 総資産
- operating_cash_flow: 営業キャッシュフロー

operation:
- current: 現在・最新の値
- max: 最大、最高、一番良い、一番多い
- min: 最小、最低、一番少ない

years:
質問に「過去10年」「5年間」など期間指定があれば整数で設定する。
期間指定がなければ null。

質問が特定の歴史的期間・具体的な年・出来事を指定している場合は、
requires_specific_period=true とする。

例:
- 「コロナ禍で売上は上がった？」
  → requires_specific_period=true
  → period_hint="コロナ禍"

- 「2020年と2022年を比較して」
  → requires_specific_period=true
  → period_hint="2020年と2022年"

「過去5期」「直近3年」のように、
最新データから相対的に取得できる期間の場合は
requires_specific_period=false とする。

specific_years:
質問に具体的な西暦年が明示されている場合、
その年を整数のリストとして設定する。

例:
- 「2020年と2022年を比較して」
  → specific_years=[2020, 2022]
  → requires_specific_period=true
  → period_hint="2020年と2022年"

- 「2023年の売上は？」
  → specific_years=[2023]
  → requires_specific_period=true
  → period_hint="2023年"

- 「過去5期で一番売上が高かったのは？」
  → specific_years=[]
  → requires_specific_period=false

- 「コロナ禍で売上は上がった？」
  → specific_years=[]
  → requires_specific_period=true
  → period_hint="コロナ禍"

具体的な年が質問に含まれていない場合は
specific_years=[] とする。


is_overall_performance:
- 売上だけ、営業利益だけなど単一の財務指標ではなく、
  会社全体の業績推移を尋ねている場合は true。
- 「ここ数年の業績は？」
- 「最近の業績推移は？」
- 「数年間の業績を教えて」
  などは true。
- 「過去5期で一番売上が高かったのは？」のような
  単一指標の質問は false。

is_overall_performance=true の場合:
- 質問で特定の財務指標が指定されていなければ metric=null とする。
- operation=current とする。
- years に明示的な期間指定がなければ null とする。

回答そのものや計算は行わず、計画だけを返してください。
""",
            output_type=FinancialQuestionPlan,
        )

    async def plan(
        self,
        question: str,
    ) -> FinancialQuestionPlan:
        result = await Runner.run(
            self.agent,
            question,
        )

        plan = FinancialQuestionPlan.model_validate(result.final_output)

        specific_years: list[int] = []

        for matched_year in re.findall(
            r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})年?",
            question,
        ):
            year = int(matched_year)

            if year not in specific_years:
                specific_years.append(year)

        if specific_years:
            return FinancialQuestionPlan(
                metric=plan.metric,
                operation=plan.operation,
                years=plan.years,
                requires_specific_period=True,
                period_hint=plan.period_hint,
                specific_years=specific_years,
                is_overall_performance=plan.is_overall_performance,
            )

        if plan.requires_specific_period:
            return plan

        normalized_question = question.replace(" ", "")

        if "業績" in normalized_question and any(
            keyword in normalized_question
            for keyword in (
                "ここ数年",
                "数年",
                "最近",
                "推移",
            )
        ):
            return FinancialQuestionPlan(
                metric=plan.metric,
                operation=plan.operation,
                years=plan.years or 5,
                requires_specific_period=(plan.requires_specific_period),
                period_hint=plan.period_hint,
                specific_years=plan.specific_years,
                is_overall_performance=True,
            )

        return plan
