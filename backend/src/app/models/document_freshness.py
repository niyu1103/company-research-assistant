from datetime import datetime

from pydantic import BaseModel, Field


class DocumentFreshness(BaseModel):
    version: str = Field(min_length=1)
    source_updated_at: datetime | None = None
    fetched_at: datetime
    indexed_at: datetime | None = None


class DocumentIndexState(BaseModel):
    doc_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    indexed_at: datetime | None = None


class DocumentIndexUpdateResult(BaseModel):
    doc_id: str
    version: str
    chunks_rebuilt: bool
    sync_required: bool
    chunk_count: int
    reason: str
    indexed_at: datetime | None = None


class DocumentIndexRefreshResult(BaseModel):
    doc_id: str
    edinet_code: str
    version: str
    chunks_rebuilt: bool
    sync_performed: bool
    chunk_count: int
    reason: str
    indexed_at: datetime | None = None
