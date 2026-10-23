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

        return FinancialQuestionPlan.model_validate(result.final_output)
