from agents import Agent, Runner

from app.models.company_question_route import (
    CompanyQuestionRoute,
)


class CompanyQuestionRouterService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Company Question Router",
            model="gpt-5.6-luna",
            instructions="""
あなたは企業リサーチ質問のルーターです。

ユーザーの質問を、必ず次の4種類のどれか1つに分類してください。

company_facts:
会社の基本的な構造化情報を直接取得すれば答えられる質問。
例:
- 従業員は何人？
- 本社はどこ？
- 設立はいつ？
- 法人番号は？
- EDINETコードは？

financial:
財務数値または財務履歴を取得・計算すれば答えられる質問。
例:
- 売上はいくら？
- 営業利益はいくら？
- 過去10年で売上が最も高かった年は？
- 売上成長率は？
- 営業利益率は？
- CAGRは？

document:
有価証券報告書などの文章を検索して答える質問。
例:
- 何の会社？
- 主な事業は？
- どんなリスクがある？
- どんな戦略を取っている？
- サイバーリスクについて何と書いてある？

analysis:
複数の情報を組み合わせた分析、評価、推論が必要な質問。
例:
- 今後成長しそう？
- この会社の強みと弱みは？
- 投資先としてどう評価する？
- 売上と事業リスクを踏まえて今後を分析して

分類ルール:
1. 構造化データだけで確定できる場合は company_facts を優先する。
2. 財務数値やその計算で確定できる場合は financial を優先する。
3. 文書の記述を読む必要がある場合は document。
4. 評価、将来予測、複数情報の統合が必要な場合は analysis。
5. analysis を必要以上に選ばない。
6. 回答そのものは作らず、分類だけを行う。
""",
            output_type=CompanyQuestionRoute,
        )

    async def route(
        self,
        question: str,
    ) -> CompanyQuestionRoute:
        result = await Runner.run(
            self.agent,
            question,
        )

        return CompanyQuestionRoute.model_validate(result.final_output)
