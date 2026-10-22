from pydantic import BaseModel


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    edinet_code: str
    section: str
    chunk_index: int
    content: str


class DocumentIndexingResult(BaseModel):
    doc_id: str
    edinet_code: str
    chunk_count: int
    business_overview_chunk_count: int
    business_risks_chunk_count: int


class RetrievedDocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    edinet_code: str
    section: str
    chunk_index: int
    content: str
    score: float
