from pydantic import BaseModel


class DocumentAnswer(BaseModel):
    answer: str
    evidence_chunk_ids: list[str]
    insufficient_context: bool
