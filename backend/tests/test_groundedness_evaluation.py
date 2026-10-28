from app.models.document_chunk import RetrievedDocumentChunk
from app.models.groundedness_eval import (
    GroundednessEvidence,
    GroundednessJudgeClaim,
    GroundednessJudgeOutput,
)
from app.services.groundedness_evaluation import (
    GroundednessEvaluationService,
)


def test_calculate_groundedness_result() -> None:
    service = GroundednessEvaluationService()

    chunks = [
        RetrievedDocumentChunk(
            chunk_id="risk_1",
            doc_id="doc_1",
            edinet_code="E00001",
            section="business_risks",
            chunk_index=1,
            content="通信障害により事業に影響する可能性があります。",
            score=1.0,
        )
    ]

    judge_output = GroundednessJudgeOutput(
        claims=[
            GroundednessJudgeClaim(
                claim="通信障害により事業に影響する可能性がある",
                supported=True,
                evidence=[
                    GroundednessEvidence(
                        chunk_id="risk_1",
                        quote=(
                            "通信障害により事業に影響する"
                            "可能性があります。"
                        ),
                    )
                ],
                reason="risk_1に記載があります。",
            ),
            GroundednessJudgeClaim(
                claim="売上高が30％減少する",
                supported=False,
                evidence=[],
                reason="Contextに数値の記載がありません。",
            ),
        ]
    )

    result = service.calculate_result(
        judge_output=judge_output,
        chunks=chunks,
    )

    assert result.score == 0.5
    assert result.passed is False
    assert result.unsupported_claims == [
        "売上高が30％減少する"
    ]

def test_unknown_evidence_chunk_is_not_supported() -> None:
    service = GroundednessEvaluationService()

    chunks = [
        RetrievedDocumentChunk(
            chunk_id="risk_1",
            doc_id="doc_1",
            edinet_code="E00001",
            section="business_risks",
            chunk_index=1,
            content="通信障害に関する記載",
            score=1.0,
        )
    ]

    judge_output = GroundednessJudgeOutput(
        claims=[
            GroundednessJudgeClaim(
                claim="売上高が30％減少する",
                supported=True,
                evidence=[
                    GroundednessEvidence(
                        chunk_id="存在しないchunk",
                        quote="売上高が30％減少する",
                    )
                ],
                reason=(
                    "Judgeが誤ってsupportedと"
                    "判定した。"
                ),
            )
        ]
    )

    result = service.calculate_result(
        judge_output=judge_output,
        chunks=chunks,
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.claims[0].supported is False
    assert result.claims[0].evidence_chunk_ids == []
    
def test_evidence_quote_must_exist_in_chunk() -> None:
    service = GroundednessEvaluationService()

    chunks = [
        RetrievedDocumentChunk(
            chunk_id="risk_1",
            doc_id="doc_1",
            edinet_code="E00001",
            section="business_risks",
            chunk_index=1,
            content=(
                "通信障害により財政状況及び"
                "経営成績に影響する可能性があります。"
            ),
            score=1.0,
        )
    ]

    judge_output = GroundednessJudgeOutput(
        claims=[
            GroundednessJudgeClaim(
                claim="業務が復旧できなくなる",
                supported=True,
                evidence=[
                    GroundednessEvidence(
                        chunk_id="risk_1",
                        quote="業務が復旧できなくなる",
                    )
                ],
                reason="Judgeは根拠があると判断した。",
            )
        ]
    )

    result = service.calculate_result(
        judge_output=judge_output,
        chunks=chunks,
    )

    assert result.score == 0.0
    assert result.passed is False
    assert result.claims[0].supported is False