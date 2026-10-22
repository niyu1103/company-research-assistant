from agents import Agent, Runner

from app.models.document_qa_eval import (
    AnswerRecallJudgment,
    AnswerRecallResult,
)


class DocumentAnswerRecallEvaluationService:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Document Answer Recall Judge",
            instructions="""
あなたはRAG回答のAnswer Recall評価担当です。

EXPECTED FACTSの各事実が、
ANSWERに含まれているかを評価してください。

ルール:
- 外部知識を使わない
- ANSWERだけを評価対象にする
- 表現が完全一致しなくても意味が同じなら一致とする
- ANSWERから推測しなければ分からない事実は一致としない
- 含まれているEXPECTED FACTの番号だけをmatched_fact_indicesに入れる
- 番号は0から始まる
""".strip(),
            model="gpt-5.6-luna",
            output_type=AnswerRecallJudgment,
        )

    async def evaluate(
        self,
        *,
        answer: str,
        expected_facts: list[str],
    ) -> AnswerRecallResult:
        if not expected_facts:
            raise ValueError("expected_facts must not be empty")

        facts_text = "\n".join(
            f"{index}: {fact}" for index, fact in enumerate(expected_facts)
        )

        result = await Runner.run(
            self.agent,
            (f"ANSWER:\n{answer}\n\nEXPECTED FACTS:\n{facts_text}"),
        )

        judgment = AnswerRecallJudgment.model_validate(result.final_output)

        matched_indices = sorted(set(judgment.matched_fact_indices))

        invalid_indices = [
            index
            for index in matched_indices
            if index < 0 or index >= len(expected_facts)
        ]

        if invalid_indices:
            raise ValueError(
                f"Answer Recall judge returned invalid fact indices: {invalid_indices}"
            )

        matched_set = set(matched_indices)

        missed_indices = [
            index for index in range(len(expected_facts)) if index not in matched_set
        ]

        recall = len(matched_indices) / len(expected_facts)

        return AnswerRecallResult(
            recall=recall,
            matched_fact_indices=matched_indices,
            missed_fact_indices=missed_indices,
            reasoning=judgment.reasoning,
        )
