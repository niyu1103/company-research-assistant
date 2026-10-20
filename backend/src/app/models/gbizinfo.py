from pydantic import BaseModel, ConfigDict, Field


class GBizInfoCompany(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    corporate_number: str
    name: str

    kana: str | None = None
    postal_code: str | None = None
    location: str | None = None
    status: str | None = None

    representative_name: str | None = None
    capital_stock: int | None = None
    employee_number: int | None = None

    business_summary: str | None = None
    company_url: str | None = None
    date_of_establishment: str | None = None
    founding_year: int | None = None

    industry: list[str] = Field(default_factory=list)
    business_items: list[str] = Field(default_factory=list)

    qualification_grade: str | None = None
    number_of_activity: str | None = None
    update_date: str | None = None


class GBizInfoResponse(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    companies: list[GBizInfoCompany] = Field(
        default_factory=list,
        alias="hojin-infos",
    )
