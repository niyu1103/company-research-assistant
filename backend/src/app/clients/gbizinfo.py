import re
import unicodedata

import httpx

from app.models.company import CompanyDetail, CompanySummary
from app.models.gbizinfo import GBizInfoResponse
from app.settings import get_settings

BASE_URL = "https://api.info.gbiz.go.jp/hojin/v2"


CORPORATE_TYPES = (
    "株式会社",
    "有限会社",
    "合同会社",
    "合資会社",
    "合名会社",
    "一般社団法人",
    "一般財団法人",
    "公益社団法人",
    "公益財団法人",
)


def normalize_company_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name)

    for corporate_type in CORPORATE_TYPES:
        normalized = normalized.replace(corporate_type, "")

    normalized = re.sub(r"\s+", "", normalized)

    return normalized.lower()


def company_sort_key(
    company: CompanySummary,
    query: str,
) -> tuple[int, int, int]:
    normalized_query = normalize_company_name(query)
    normalized_name = normalize_company_name(company.name)

    if normalized_name == normalized_query:
        match_rank = 0
    elif normalized_name.startswith(normalized_query):
        match_rank = 1
    elif normalized_query in normalized_name:
        match_rank = 2
    else:
        match_rank = 3

    closed_rank = 1 if company.status == "閉鎖" else 0

    try:
        activity_count = int(company.number_of_activity or 0)
    except ValueError:
        activity_count = 0

    return (
        match_rank,
        closed_rank,
        -activity_count,
    )


class GBizInfoClient:
    def __init__(self) -> None:
        settings = get_settings()

        self.headers = {
            "X-hojinInfo-api-token": settings.gbizinfo_api_key,
            "Accept": "application/json",
        }

    async def search_companies(
        self,
        name: str,
    ) -> list[CompanySummary]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/hojin",
                headers=self.headers,
                params={"name": name},
                timeout=30.0,
            )

            response.raise_for_status()

            data = GBizInfoResponse.model_validate_json(response.text)

            results = [
                CompanySummary(
                    corporate_number=company.corporate_number,
                    name=company.name,
                    postal_code=company.postal_code,
                    location=company.location,
                    status=company.status,
                    number_of_activity=company.number_of_activity,
                    update_date=company.update_date,
                )
                for company in data.companies
            ]

            results.sort(
                key=lambda company: company_sort_key(
                    company,
                    name,
                )
            )

            return results

    async def get_company(
        self,
        corporate_number: str,
    ) -> CompanyDetail | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/hojin/{corporate_number}",
                headers=self.headers,
                timeout=30.0,
            )

            response.raise_for_status()

            data = GBizInfoResponse.model_validate_json(response.text)

            if not data.companies:
                return None

            company = data.companies[0]

            return CompanyDetail(
                corporate_number=company.corporate_number,
                name=company.name,
                kana=company.kana,
                postal_code=company.postal_code,
                location=company.location,
                status=company.status,
                representative_name=company.representative_name,
                capital_stock=company.capital_stock,
                employee_number=company.employee_number,
                business_summary=company.business_summary,
                company_url=company.company_url,
                date_of_establishment=company.date_of_establishment,
                founding_year=company.founding_year,
                industry=company.industry,
                business_items=company.business_items,
                qualification_grade=company.qualification_grade,
                update_date=company.update_date,
            )
