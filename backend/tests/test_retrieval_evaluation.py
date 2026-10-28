from pathlib import Path

from app.services.retrieval_evaluation import (
    RetrievalEvaluationService,
)


def test_load_retrieval_eval_cases() -> None:
    service = RetrievalEvaluationService()

    cases = service.load_cases(
        Path("evals/retrieval_cases.json"),
    )
    
    

    assert len(cases) >= 8

    case_ids = {
        case.id
        for case in cases
    }

    assert "headwaters-ai-competition" in case_ids
    assert "nintendo-cyber-risk" in case_ids

    assert cases[0].id == "headwaters-ai-competition"
    assert cases[0].company_name == "株式会社ヘッドウォータース"
    assert cases[0].expected_chunk_ids == [
        "S100XUSL_business_risks_0"
    ]

def test_calculate_retrieval_metrics() -> None:
    service = RetrievalEvaluationService()

    metrics = service.calculate_metrics(
        expected_chunk_ids=[
            "S100XUSL_business_risks_1",
        ],
        retrieved_chunk_ids=[
            "S100XUSL_business_risks_0",
            "S100XUSL_business_risks_1",
            "S100XUSL_business_risks_2",
        ],
        k=3,
    )

    assert metrics.recall_at_k == 1.0
    assert metrics.precision_at_k == 1 / 3
    assert metrics.reciprocal_rank == 0.5

def test_precision_at_k_uses_k_as_denominator() -> None:
    service = RetrievalEvaluationService()

    metrics = service.calculate_metrics(
        expected_chunk_ids=[
            "S100XUSL_business_risks_1",
        ],
        retrieved_chunk_ids=[
            "S100XUSL_business_risks_1",
        ],
        k=3,
    )

    assert metrics.recall_at_k == 1.0
    assert metrics.precision_at_k == 1 / 3
    assert metrics.reciprocal_rank == 1.0