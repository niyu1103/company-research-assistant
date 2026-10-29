import json
from pathlib import Path

from agents import Agent, Runner
from pydantic import TypeAdapter

from app.models.answer_relevance_eval import (
    AnswerRelevanceEvalCase,
    AnswerRelevanceEvalResult,
    AnswerRelevanceJudgeOutput,
)


answer_relevance_agent = Agent(
    name="Answer Relevance Evaluator",
    instructions="""
あなたはQAシステムの回答が、
ユーザーの質問に関連した回答になっているかを評価するJudgeです。

QuestionとAnswerだけを使って判定してください。

評価対象はAnswer Relevanceだけです。

次のことは評価しないでください。
- 回答内容が事実として正しいか
- Retrieved Contextに根拠があるか
- 外部知識と一致しているか
- 回答が完全かどうか

relevant=trueにする条件:
- 質問の主要な意図に直接答えている
- または、質問に答えるための情報が不足していることを
  直接かつ明確に説明している

relevant=falseにする条件:
- 質問とは別の話をしている
- 関連する話題ではあるが、
  質問で聞かれている内容には答えていない
- 質問の対象を別の概念に置き換えて回答している

重要:
関連する情報を述べているだけでは
relevant=trueにしないでください。

例:

Question:
「会社の社風は？」

Answer:
「この会社はAIシステムを開発しています。」

→ false

Question:
「会社の社風は？」

Answer:
「提供された情報には、社風を直接説明する記載がありません。」

→ true

Question:
「本社はどこ？」

Answer:
「東京都新宿区です。」

→ true

Question:
「本社はどこ？」

Answer:
「ソフトウェア開発会社です。」

→ false

reasonは日本語で簡潔に説明してください。
""",
    output_type=AnswerRelevanceJudgeOutput,
)


class AnswerRelevanceEvaluationService:
    _cases_adapter = TypeAdapter(
        list[AnswerRelevanceEvalCase]
    )

    def load_cases(
        self,
        path: Path,
    ) -> list[AnswerRelevanceEvalCase]:
        raw: object = json.loads(
            path.read_text(encoding="utf-8"),
        )

        return self._cases_adapter.validate_python(
            raw,
        )

    async def evaluate(
        self,
        *,
        question: str,
        answer: str,
    ) -> AnswerRelevanceEvalResult:
        prompt = (
            f"Question:\n{question}\n\n"
            f"Answer:\n{answer}"
        )

        result = await Runner.run(
            answer_relevance_agent,
            input=prompt,
        )

        judge_output = (
            AnswerRelevanceJudgeOutput.model_validate(
                result.final_output,
            )
        )

        return AnswerRelevanceEvalResult(
            relevant=judge_output.relevant,
            reason=judge_output.reason,
        )