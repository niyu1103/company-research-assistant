import json
from pathlib import Path

from agents import Agent, Runner
from pydantic import TypeAdapter

from app.models.context_sufficiency_eval import (
    ContextSufficiencyEvalCase,
    ContextSufficiencyEvalResult,
    ContextSufficiencyJudgeOutput,
)
from app.models.document_chunk import RetrievedDocumentChunk

context_sufficiency_agent = Agent(
    name="Context Sufficiency Evaluator",
    instructions="""
あなたはRAGのRetrieved Contextが、
ユーザーの質問に答えるために十分かを評価するJudgeです。

質問とRetrieved Contextだけを使って判定してください。

重要:
- 外部知識や一般常識を使わないでください。
- Contextに関連情報があるだけではsufficient=trueにしないでください。
- 質問で聞かれている内容そのものを、
  Contextから直接説明できる場合のみsufficient=trueにしてください。
- 推測や解釈を追加しないと回答できない場合は、
  sufficient=falseにしてください。
- 一部しか答えられない場合も、
  質問の主要部分が不足していればfalseにしてください。

特に注意:
事業方針、商品開発姿勢、経営理念などの記載だけから、
「社風」「企業文化」「働き方」などを推測してはいけません。

sufficient=trueの場合:
- evidenceを1件以上返してください。
- quoteはRetrieved Contextに実際に存在する文章を
  短くそのままコピーしてください。
- quoteを要約・言い換えしてはいけません。

sufficient=falseの場合:
- evidenceは空配列で構いません。
- missing_informationに、
  質問へ答えるために不足している情報を記載してください。

日本語でreasonを簡潔に説明してください。
""",
    output_type=ContextSufficiencyJudgeOutput,
)


class ContextSufficiencyEvaluationService:
    _cases_adapter = TypeAdapter(list[ContextSufficiencyEvalCase])

    def load_cases(
        self,
        path: Path,
    ) -> list[ContextSufficiencyEvalCase]:
        raw: object = json.loads(
            path.read_text(encoding="utf-8"),
        )

        return self._cases_adapter.validate_python(
            raw,
        )

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        return "".join(value.split())

    def calculate_result(
        self,
        *,
        judge_output: ContextSufficiencyJudgeOutput,
        chunks: list[RetrievedDocumentChunk],
    ) -> ContextSufficiencyEvalResult:
        valid_evidence_chunk_ids: list[str] = []

        for evidence in judge_output.evidence:
            matching_chunk = next(
                (chunk for chunk in chunks if chunk.chunk_id == evidence.chunk_id),
                None,
            )

            if matching_chunk is None:
                continue

            content = self._normalize_text(
                matching_chunk.content,
            )

            quote = self._normalize_text(
                evidence.quote,
            )

            if quote not in content:
                continue

            valid_evidence_chunk_ids.append(
                evidence.chunk_id,
            )

        sufficient = judge_output.sufficient

        if sufficient and not valid_evidence_chunk_ids:
            sufficient = False

        return ContextSufficiencyEvalResult(
            sufficient=sufficient,
            evidence_chunk_ids=(valid_evidence_chunk_ids if sufficient else []),
            missing_information=(judge_output.missing_information),
            reason=judge_output.reason,
        )

    async def evaluate(
        self,
        *,
        question: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> ContextSufficiencyEvalResult:
        context = "\n\n".join(
            (f"chunk_id: {chunk.chunk_id}\ncontent:\n{chunk.content}")
            for chunk in chunks
        )

        prompt = f"質問:\n{question}\n\nRetrieved Context:\n{context}"

        result = await Runner.run(
            context_sufficiency_agent,
            input=prompt,
        )

        judge_output = ContextSufficiencyJudgeOutput.model_validate(
            result.final_output,
        )

        return self.calculate_result(
            judge_output=judge_output,
            chunks=chunks,
        )
