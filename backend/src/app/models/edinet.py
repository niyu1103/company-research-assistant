from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class EdinetApiDocument(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    doc_id: str = Field(alias="docID")
    edinet_code: str | None = Field(
        default=None,
        alias="edinetCode",
    )
    sec_code: str | None = Field(
        default=None,
        alias="secCode",
    )
    corporate_number: str | None = Field(
        default=None,
        alias="JCN",
    )
    filer_name: str | None = Field(
        default=None,
        alias="filerName",
    )
    doc_type_code: str | None = Field(
        default=None,
        alias="docTypeCode",
    )
    form_code: str | None = Field(
        default=None,
        alias="formCode",
    )
    ordinance_code: str | None = Field(
        default=None,
        alias="ordinanceCode",
    )

    period_start: date | None = Field(
        default=None,
        alias="periodStart",
    )
    period_end: date | None = Field(
        default=None,
        alias="periodEnd",
    )
    submitted_at: datetime | None = Field(
        default=None,
        alias="submitDateTime",
    )

    description: str | None = Field(
        default=None,
        alias="docDescription",
    )
    xbrl_flag: str | None = Field(
        default=None,
        alias="xbrlFlag",
    )
    pdf_flag: str | None = Field(
        default=None,
        alias="pdfFlag",
    )
    csv_flag: str | None = Field(
        default=None,
        alias="csvFlag",
    )


class EdinetDocumentsResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    results: list[EdinetApiDocument] = Field(default_factory=list)


class EdinetDocument(BaseModel):
    doc_id: str
    edinet_code: str | None = None
    sec_code: str | None = None
    corporate_number: str | None = None
    filer_name: str | None = None
    doc_type_code: str | None = None
    form_code: str | None = None
    ordinance_code: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    submitted_at: datetime | None = None
    description: str | None = None
    xbrl_available: bool = False
    pdf_available: bool = False
    csv_available: bool = False
    source_updated_at: datetime | None = None
    fetched_at: datetime


class EdinetCsvPreview(BaseModel):
    file_name: str | None
    headers: list[str]
    rows: list[list[str]]


class EdinetCsvSearchResult(BaseModel):
    element_id: str
    item_name: str
    context_id: str | None = None
    relative_year: str | None = None
    consolidated_or_non_consolidated: str | None = None
    period_type: str | None = None
    unit: str | None = None
    value: str | None = None


class EdinetCsvRow(BaseModel):
    element_id: str
    item_name: str = ""
    context_id: str = ""
    relative_year: str = ""
    consolidated_or_non_consolidated: str = ""
    period_type: str = ""
    unit: str = ""
    value: str = ""
