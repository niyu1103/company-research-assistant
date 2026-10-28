import json
from pathlib import Path

from pydantic import TypeAdapter

from app.models.retrieval_eval import (
    RetrievalEvalCase,
    RetrievalEvalMetrics,
)


class RetrievalEvaluationService:
    _cases_adapter = TypeAdapter(list[RetrievalEvalCase])

    def load_cases(
        self,
        path: Path,
    ) -> list[RetrievalEvalCase]:
        raw: object = json.loads(
            path.read_text(encoding="utf-8"),
        )

        return self._cases_adapter.validate_python(raw)

    def calculate_metrics(
        self,
        *,
        expected_chunk_ids: list[str],
        retrieved_chunk_ids: list[str],
        k: int,
    ) -> RetrievalEvalMetrics:
        if k < 1:
            raise ValueError("k must be at least 1")

        expected = set(expected_chunk_ids)
        retrieved_at_k = retrieved_chunk_ids[:k]

        matched = expected.intersection(retrieved_at_k)

        recall_at_k = len(matched) / len(expected)

        precision_at_k = len(matched) / k

        reciprocal_rank = 0.0

        for rank, chunk_id in enumerate(
            retrieved_at_k,
            start=1,
        ):
            if chunk_id in expected:
                reciprocal_rank = 1 / rank
                break

        return RetrievalEvalMetrics(
            recall_at_k=recall_at_k,
            precision_at_k=precision_at_k,
            reciprocal_rank=reciprocal_rank,
        )
