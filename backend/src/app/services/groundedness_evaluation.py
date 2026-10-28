from agents import Agent, Runner, set_default_openai_key

from app.models.document_chunk import RetrievedDocumentChunk
from app.models.groundedness_eval import (
    GroundednessClaimEvaluation,
    GroundednessContextChunk,
    GroundednessEvalInput,
    GroundednessEvalResult,
    GroundednessJudgeOutput,
)
from app.settings import get_settings

groundedness_evaluation_agent = Agent(
    name="Groundedness Evaluator",
    instructions="""
あなたはRAG回答のGroundednessを評価するJudgeです。

質問、回答、Retrieved Contextが与えられます。

まず回答を、根拠を確認可能な事実的な主張
(claim)ごとに分解してください。

その後、それぞれのclaimについて、
Retrieved Contextだけを使って
supportedかどうか判定してください。

重要なルール:
- Retrieved Context以外の知識を使わないでください。
- 一般常識や外部知識で補完しないでください。
- 現実世界で正しいかではなく、
  Contextから裏付けられるかを評価してください。
- 数値、原因、結果、時期、条件、比較、断定など、
  Contextにない情報はsupported=falseにしてください。
- Contextの自然な言い換えはsupported=trueで構いません。
- 単なる文体上の表現はclaimとして分割しないでください。
- 1つのclaimには、原則として1つの検証可能な主張を含めてください。

evidence_chunk_idsについて:
- supported=trueの場合は、
  根拠となるchunk_idを1件以上指定してください。
- supported=falseの場合は空配列にしてください。
- 入力に存在しないchunk_idを作らないでください。

scoreやpassedは判定しないでください。
各claimについてのみ評価してください。

supported=true と判断する場合は、
必ず evidence に根拠を指定してください。

evidence.quote は、
Retrieved Context内に実際に存在する文章を
短くそのままコピーしてください。

要約、言い換え、推測した文章を
evidence.quote に使用してはいけません。

supported=false の場合、
evidence は空配列にしてください。

Contextに書かれた対策から、
事故発生時の結果を逆算してはいけません。

例えば、
「早期復旧に備えている」
という記載だけから、
「業務が復旧できなくなる」
という主張をsupportedにしてはいけません。

日本語でreasonを簡潔に説明してください。
""",
    output_type=GroundednessJudgeOutput,
)


class GroundednessEvaluationService:
    def calculate_result(
        self,
        *,
        judge_output: GroundednessJudgeOutput,
        chunks: list[RetrievedDocumentChunk],
    ) -> GroundednessEvalResult:

        claims: list[GroundednessClaimEvaluation] = []

        for claim in judge_output.claims:
            valid_evidence_chunk_ids: list[str] = []

            for evidence in claim.evidence:
                matching_chunk = next(
                    (chunk for chunk in chunks if chunk.chunk_id == evidence.chunk_id),
                    None,
                )

                if matching_chunk is None:
                    continue

                normalized_content = self._normalize_text(
                    matching_chunk.content,
                )

                normalized_quote = self._normalize_text(
                    evidence.quote,
                )

                if normalized_quote not in normalized_content:
                    continue

                valid_evidence_chunk_ids.append(
                    evidence.chunk_id,
                )

            supported = claim.supported and bool(valid_evidence_chunk_ids)

            claims.append(
                GroundednessClaimEvaluation(
                    claim=claim.claim,
                    supported=supported,
                    evidence_chunk_ids=(valid_evidence_chunk_ids if supported else []),
                    reason=claim.reason,
                )
            )

        supported_count = sum(claim.supported for claim in claims)

        total_count = len(claims)

        score = supported_count / total_count

        passed = supported_count == total_count

        unsupported_claims = [claim.claim for claim in claims if not claim.supported]

        return GroundednessEvalResult(
            score=score,
            passed=passed,
            claims=claims,
            unsupported_claims=unsupported_claims,
            reason=(
                f"{total_count}件中"
                f"{supported_count}件の主張が"
                "Retrieved Contextで"
                "裏付けられています。"
            ),
        )

    async def evaluate(
        self,
        *,
        question: str,
        answer: str,
        chunks: list[RetrievedDocumentChunk],
    ) -> GroundednessEvalResult:
        settings = get_settings()

        set_default_openai_key(
            settings.openai_api_key,
        )

        evaluation_input = GroundednessEvalInput(
            question=question,
            answer=answer,
            context_chunks=[
                GroundednessContextChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                )
                for chunk in chunks
            ],
        )

        result = await Runner.run(
            groundedness_evaluation_agent,
            input=evaluation_input.model_dump_json(
                ensure_ascii=False,
            ),
        )

        judge_output = GroundednessJudgeOutput.model_validate(
            result.final_output,
        )

        return self.calculate_result(
            judge_output=judge_output,
            chunks=chunks,
        )

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        return "".join(value.split())
