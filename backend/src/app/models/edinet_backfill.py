from datetime import date

from pydantic import BaseModel

from app.models.edinet_sync import EdinetSyncResult


class EdinetBackfillResult(BaseModel):
    start_date: date
    end_date: date
    requested_days: int
    batch_count: int
    batches: list[EdinetSyncResult]
