from agents import Agent, Runner

from app.models.document_query import DocumentQueryPlan


class DocumentQueryPlanningService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Document Search Query Planner",
            instructions="""
あなたは企業文書検索のための検索クエリ生成担当です。

ユーザーの質問に回答してはいけません。
質問から、文書検索に最も有効な短い検索語を抽出してください。

ルール:
- 企業名は検索対象企業を識別するだけなら除外する
- 「について」「教えて」「事業へのリスク」などの一般的な表現は除外する
- 検索対象を特定する重要な名詞・専門用語を優先する
- 原文にある重要な語はできるだけ維持する
- 不要に検索語を増やさない
- 1つの短い検索クエリを返す
""".strip(),
            model="gpt-5.6-luna",
            output_type=DocumentQueryPlan,
        )

    async def plan(
        self,
        question: str,
    ) -> DocumentQueryPlan:
        question = question.strip()

        if not question:
            raise ValueError("question must not be empty")

        result = await Runner.run(
            self.agent,
            question,
        )

        return DocumentQueryPlan.model_validate(result.final_output)
