from app.models.context_sufficiency_eval import (
    ContextSufficiencyEvidence,
    ContextSufficiencyJudgeOutput,
)
from app.models.document_chunk import RetrievedDocumentChunk
from app.services.context_sufficiency_evaluation import (
    ContextSufficiencyEvaluationService,
)


def test_sufficient_context_with_valid_evidence() -> None:
    service = ContextSufficiencyEvaluationService()

    chunks = [
        RetrievedDocumentChunk(
            chunk_id="risk_1",
            doc_id="doc_1",
            edinet_code="E00001",
            section="business_risks",
            chunk_index=1,
            content=(
                "通信障害により経営成績に"
                "影響する可能性があります。"
            ),
            score=1.0,
        )
    ]

    judge_output = ContextSufficiencyJudgeOutput(
        sufficient=True,
        evidence=[
            ContextSufficiencyEvidence(
                chunk_id="risk_1",
                quote=(
                    "通信障害により経営成績に"
                    "影響する可能性があります。"
                ),
            )
        ],
        missing_information=[],
        reason="質問に直接答えられる記載があります。",
    )

    result = service.calculate_result(
        judge_output=judge_output,
        chunks=chunks,
    )

    assert result.sufficient is True
    assert result.evidence_chunk_ids == [
        "risk_1"
    ]


def test_invalid_evidence_makes_context_insufficient() -> None:
    service = ContextSufficiencyEvaluationService()

    chunks = [
        RetrievedDocumentChunk(
            chunk_id="overview_1",
            doc_id="doc_1",
            edinet_code="E00001",
            section="business_overview",
            chunk_index=1,
            content="新しい価値の創出に取り組んでいます。",
            score=1.0,
        )
    ]

    judge_output = ContextSufficiencyJudgeOutput(
        sufficient=True,
        evidence=[
            ContextSufficiencyEvidence(
                chunk_id="overview_1",
                quote="自由闊達な社風です。",
            )
        ],
        missing_information=[],
        reason="社風を説明できると判断した。",
    )

    result = service.calculate_result(
        judge_output=judge_output,
        chunks=chunks,
    )

    assert result.sufficient is False
    assert result.evidence_chunk_ids == []