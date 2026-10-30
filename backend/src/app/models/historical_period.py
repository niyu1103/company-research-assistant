from pydantic import BaseModel, Field


class HistoricalPeriodResolution(BaseModel):
    label: str

    resolved: bool = False

    start_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )
    end_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    reason: str | None = None
