from agents import Agent, Runner

from app.models.document_qa_eval import (
    GroundednessJudgment,
)


class DocumentGroundednessEvaluationService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Document Groundedness Judge",
            instructions="""
あなたはRAG回答のGroundedness評価担当です。

ANSWERに含まれる事実的主張が、
CONTEXTによって裏付けられているかを評価してください。

ルール:
- 外部知識を使って正しさを補完しない
- CONTEXTだけを根拠に判断する
- ANSWER内の主要な事実的主張を確認する
- CONTEXTに裏付けがない主張をunsupported_claimsに入れる
- 表現が完全一致しなくても、意味として裏付けられていればgroundedとみなす
- scoreは0.0〜1.0
- 全ての主要主張が裏付けられていればgrounded=true
- 1つでも重要な未根拠主張があればgrounded=false
""".strip(),
            model="gpt-5.6-luna",
            output_type=GroundednessJudgment,
        )

    async def evaluate(
        self,
        *,
        answer: str,
        context: str,
    ) -> GroundednessJudgment:
        result = await Runner.run(
            self.agent,
            (f"ANSWER:\n{answer}\n\nCONTEXT:\n{context}"),
        )

        return GroundednessJudgment.model_validate(result.final_output)
