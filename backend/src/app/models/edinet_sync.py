from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class EdinetSyncItem(BaseModel):
    date: date
    status: Literal["synced", "skipped"]
    saved_count: int = Field(ge=0)


class EdinetSyncResult(BaseModel):
    status: Literal["ok"] = "ok"
    start_date: date
    end_date: date
    days: int = Field(ge=1)
    total_saved: int = Field(ge=0)
    results: list[EdinetSyncItem] = Field(default_factory=list)

    has_more: bool = False
    next_start_date: date | None = None


class EdinetSyncUpToDateResult(BaseModel):
    status: Literal["ok"] = "ok"
    message: Literal["Already up to date"] = "Already up to date"
    latest_sync_date: date
    has_more: Literal[False] = False
    next_start_date: None = None


type EdinetSyncLatestResult = EdinetSyncResult | EdinetSyncUpToDateResult
